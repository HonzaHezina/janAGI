import { BaseProvider, getOpenAILikeModel } from '~/lib/modules/llm/base-provider';
import type { ModelInfo } from '~/lib/modules/llm/types';
import type { IProviderSetting } from '~/types/model';
import type { LanguageModelV1 } from 'ai';
import { logger } from '~/utils/logger';

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
}
