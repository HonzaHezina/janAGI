import { BaseProvider, getOpenAILikeModel } from '~/lib/modules/llm/base-provider';
import type { ModelInfo } from '~/lib/modules/llm/types';
import type { IProviderSetting } from '~/types/model';
import type { LanguageModelV1 } from 'ai';
import { logger } from '~/utils/logger';
// Note: MCP Agent provider integrates with the local mcp-agent FastAPI.
// It exposes additional helper methods for agent CRUD and plan streaming.

export default class MCPAgentProvider extends BaseProvider {
  name = 'MCPAgent';
  getApiKeyLink = undefined; // MCP Agent nepotřebuje API klíč v bolt.diy

  config = {
    baseUrlKey: 'MCP_AGENT_API_BASE_URL',
    baseUrl: 'http://127.0.0.1:8000/v1', // FastAPI server z llm_mcp_app
    apiTokenKey: '', // Nepotřebujeme API token pro lokální MCP Agent
  };

  staticModels: ModelInfo[] = [
    // Pouze jeden hlavní model pro orchestraci
    {
      name: 'mcp-orchestrator',
      label: 'MCP Agent Orchestrator',
      provider: this.name,
      maxTokenAllowed: 8192,
    },
  ];

  async getDynamicModels(
    apiKeys?: Record<string, string>,
    settings?: IProviderSetting,
    serverEnv: Record<string, string> = {},
  ): Promise<ModelInfo[]> {
    let baseUrl = this.config.baseUrl;

    if (!baseUrl) {
      logger.error('No baseUrl found for MCPAgent provider');
      return [];
    }

    // Pokud bolt.diy běží v Dockeru, upravíme localhost na host.docker.internal
    if (typeof window === 'undefined') {
      const isDocker = process?.env?.RUNNING_IN_DOCKER === 'true' || serverEnv?.RUNNING_IN_DOCKER === 'true';
      if (isDocker) {
        baseUrl = baseUrl.replace('localhost', 'host.docker.internal').replace('127.0.0.1', 'host.docker.internal');
      }
    }

    logger.info(`Fetching models from MCP Agent at: ${baseUrl}/models`);

    try {
      const response = await fetch(`${baseUrl}/models`);
      if (!response.ok) {
        const errorText = await response.text();
        logger.error(`Failed to fetch models from MCP Agent: ${response.status} - ${errorText}`);
        throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
      }
      
      const data = (await response.json()) as { data: Array<{ id: string; object: string; owned_by: string }> };

      // Vrátíme pouze statické modely - agenty jsou interní
      return this.staticModels;
    } catch (error) {
      logger.error(`Error fetching models from MCPAgent: ${error}`);
      return [];
    }
  }

  getModelInstance(options: {
    model: string;
    serverEnv: Env;
    apiKeys?: Record<string, string>;
    providerSettings?: Record<string, IProviderSetting>;
  }): LanguageModelV1 {
    const { model, serverEnv, apiKeys, providerSettings } = options;

    let baseUrl = this.config.baseUrl;

    if (!baseUrl) {
      throw new Error(`Missing base URL for ${this.name} provider`);
    }

    // Zpracování Docker prostředí
    const isDocker = process?.env?.RUNNING_IN_DOCKER === 'true' || serverEnv?.RUNNING_IN_DOCKER === 'true';

    if (typeof window === 'undefined') {
      if (isDocker) {
        baseUrl = baseUrl.replace('localhost', 'host.docker.internal').replace('127.0.0.1', 'host.docker.internal');
      }
    }

    logger.debug(`MCPAgent Base URL used: ${baseUrl}`);
    logger.debug(`Getting model instance for: ${model} with base URL: ${baseUrl}`);

    // MCP Agent emuluje OpenAI API, takže můžeme použít getOpenAILikeModel
    // API klíč není potřeba, protože MCP Agent má vlastní autentizaci vůči Gemini
    return getOpenAILikeModel(baseUrl, '', model);
  }

  // --- Agent code CRUD operations ------------------------------------------------
  async getAgentCode(name: string): Promise<{ name?: string; code?: string; detail?: string }> {
    const baseUrl = this.config.baseUrl;
    try {
      const res = await fetch(`${baseUrl}/agents/${encodeURIComponent(name)}/code`);
      if (!res.ok) {
        const txt = await res.text();
        logger.error(`getAgentCode failed: ${res.status} - ${txt}`);
        return { detail: `HTTP ${res.status}: ${txt}` };
      }
      return await res.json();
    } catch (err) {
      logger.error(`getAgentCode error: ${err}`);
      return { detail: String(err) };
    }
  }

  async putAgentCode(name: string, code: string): Promise<{ detail?: string; agents?: string[] }> {
    const baseUrl = this.config.baseUrl;
    try {
      const res = await fetch(`${baseUrl}/agents/${encodeURIComponent(name)}/code`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code }),
      });
      if (!res.ok) {
        const txt = await res.text();
        logger.error(`putAgentCode failed: ${res.status} - ${txt}`);
        return { detail: `HTTP ${res.status}: ${txt}` };
      }
      return await res.json();
    } catch (err) {
      logger.error(`putAgentCode error: ${err}`);
      return { detail: String(err) };
    }
  }

  // --- Plan execution streaming (SSE-like) ---------------------------------------
  //
  // The backend exposes POST /v1/plan/stream which returns Server-Sent Events text stream.
  // Browsers cannot send a POST with EventSource, so we use fetch + ReadableStream parsing
  // of SSE "data: ..." frames. The onEvent callback receives parsed JSON objects when possible.
  //
  // Helper: requestPlan -> asks the orchestration LLM to produce a structured plan (JSON preferred).
  // Helper: approveAndExecute -> convert structured plan to textual plan lines and stream execution.
  //
  async requestPlan(userPrompt: string): Promise<{ assistant?: string; plan?: any; error?: string }> {
    const baseUrl = this.config.baseUrl;
    try {
      const res = await fetch(`${baseUrl}/chat/completions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: 'mcp-orchestrator',
          messages: [{ role: 'user', content: userPrompt }],
          temperature: 0.3
        })
      });
      if (!res.ok) {
        const txt = await res.text();
        logger.error(`requestPlan failed: ${res.status} - ${txt}`);
        return { error: `HTTP ${res.status}: ${txt}` };
      }
      const json: any = await res.json();
      const assistant = json.choices?.[0]?.message?.content ?? '';
      // Backend may attach plan_json top-level (fastapi returned response_content with plan_json)
      const planCandidate = (json as any).plan_json ?? this.extractFirstJson(assistant);
      return { assistant, plan: planCandidate ?? undefined };
    } catch (err: any) {
      logger.error(`requestPlan error: ${err}`);
      return { error: String(err) };
    }
  }

  extractFirstJson(text: string) {
    if (!text || typeof text !== 'string') return null;
    const start = text.indexOf('{');
    if (start === -1) return null;
    let depth = 0;
    for (let i = start; i < text.length; i++) {
      const ch = text[i];
      if (ch === '{') depth++;
      else if (ch === '}') {
        depth--;
        if (depth === 0) {
          try {
            return JSON.parse(text.slice(start, i + 1));
          } catch (e) {
            return null;
          }
        }
      }
    }
    return null;
  }

  planToText(planObj: any): string {
    // Convert structured plan ({"plan":[...]}) into textual lines consumed by the executor.
    if (!planObj) return '';
    const steps = Array.isArray(planObj.plan) ? planObj.plan : (Array.isArray(planObj) ? planObj : []);
    const lines: string[] = [];
    for (let i = 0; i < steps.length; i++) {
      const step = steps[i] || {};
      const num = step.step ?? step.index ?? (i + 1);
      const desc = (step.description ?? '').toString();
      const agent = (step.agent ?? '').toString();
      const args = step.arguments ?? {};
      let argsText = '';
      try {
        argsText = JSON.stringify(args);
      } catch {
        argsText = String(args);
      }
      lines.push(`${num}. ${desc} - agent: ${agent}, arguments: ${argsText}`);
    }
    return lines.join('\n');
  }

  approveAndExecute(planObj: any, onEvent: (event: any) => void): { cancel: () => void } {
    // Convert structured plan into textual plan and call streamPlan to execute with SSE-like events.
    const planText = this.planToText(planObj);
    return this.streamPlan(planText, 'mcp-orchestrator', onEvent);
  }

  streamPlan(
    planText: string,
    model: string = 'mcp-orchestrator',
    onEvent: (event: any) => void,
  ): { cancel: () => void } {
    const baseUrl = this.config.baseUrl;
    const controller = new AbortController();
    const url = `${baseUrl}/plan/stream`;

    (async () => {
      try {
        const res = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ plan: planText, model }),
          signal: controller.signal,
        });
        if (!res.ok) {
          const txt = await res.text();
          logger.error(`plan_stream failed: ${res.status} - ${txt}`);
          onEvent({ type: 'error', error: `HTTP ${res.status}: ${txt}` });
          return;
        }

        const reader = res.body?.getReader();
        if (!reader) {
          onEvent({ type: 'error', error: 'No stream reader available' });
          return;
        }

        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });

          // SSE frames are separated by double newlines; process complete frames
          let idx;
          while ((idx = buffer.indexOf('\n\n')) !== -1) {
            const raw = buffer.slice(0, idx).trim();
            buffer = buffer.slice(idx + 2);
            // Each raw may contain multiple "data: " lines; collect them
            const lines = raw.split(/\r?\n/).map(l => l.trim()).filter(Boolean);
            for (const line of lines) {
              if (line.startsWith('data:')) {
                const payload = line.slice(5).trim();
                try {
                  const parsed = JSON.parse(payload);
                  onEvent(parsed);
                } catch (e) {
                  // not JSON — send raw
                  onEvent({ raw: payload });
                }
              } else {
                // ignore other SSE meta lines
              }
            }
          }
        }

        // flush remaining buffer if any
        if (buffer.trim()) {
          const lines = buffer.split(/\r?\n/).map(l => l.trim()).filter(Boolean);
          for (const line of lines) {
            if (line.startsWith('data:')) {
              const payload = line.slice(5).trim();
              try {
                const parsed = JSON.parse(payload);
                onEvent(parsed);
              } catch {
                onEvent({ raw: payload });
              }
            }
          }
        }

        onEvent({ type: 'finished' });
      } catch (err: any) {
        if (err.name === 'AbortError') {
          onEvent({ type: 'cancelled' });
        } else {
          logger.error(`streamPlan error: ${err}`);
          onEvent({ type: 'error', error: String(err) });
        }
      }
    })();

    return {
      cancel: () => controller.abort(),
    };
  }
}
