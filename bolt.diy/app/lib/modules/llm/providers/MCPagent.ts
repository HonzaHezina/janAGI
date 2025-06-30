import { BaseProvider, getOpenAILikeModel } from '~/lib/modules/llm/base-provider';
import type { ModelInfo } from '~/lib/modules/llm/types';
import type { IProviderSetting } from '~/types/model';
import type { LanguageModelV1 } from 'ai';
import { logger } from '~/utils/logger'; // Důležité pro ladění

export default class MCPAgentProvider extends BaseProvider {
  name = 'MCPAgent'; // Jméno providera, které se zobrazí v UI bolt.diy
  getApiKeyLink = undefined; // mcp-agent nepotřebuje přímý API klíč, ten je pro Gemini uvnitř agenta

  config = {
    baseUrlKey: 'MCP_AGENT_API_BASE_URL', // Klíč pro URL v .env.local
    baseUrl: 'http://127.0.0.1:8000/v1', // Změněno zde
    apiTokenKey: '', // mcp-agent jako proxy nepotřebuje API token přímo v bolt.diy
  };

  staticModels: ModelInfo[] = []; // Pokud by mcp-agent dynamicky hlásil modely, bylo by to zde

  async getDynamicModels(
    apiKeys?: Record<string, string>,
    settings?: IProviderSetting,
    serverEnv: Record<string, string> = {},
  ): Promise<ModelInfo[]> {
    let baseUrl = this.config.baseUrl; // Změněno zde

    if (!baseUrl) {
      logger.error('No baseUrl found for MCPAgent provider');
      return []; // Vracíme prázdné pole, pokud není nastaveno URL
    }

    // Pokud bolt.diy běží v Dockeru, je třeba upravit localhost
    if (typeof window === 'undefined') { // Běží na serveru (Node.js)
      const isDocker = process?.env?.RUNNING_IN_DOCKER === 'true' || serverEnv?.RUNNING_IN_DOCKER === 'true';
      if (isDocker) {
        baseUrl = baseUrl.replace('localhost', 'host.docker.internal').replace('127.0.0.1', 'host.docker.internal');
      }
    }

    logger.info(`Fetching models from MCP Agent at: ${baseUrl}/models`); // Změněno zde

    try {
      const response = await fetch(`${baseUrl}/models`); // Změněno zde
      if (!response.ok) {
        const errorText = await response.text();
        logger.error(`Failed to fetch models from MCP Agent: ${response.status} - ${errorText}`);
        throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
      }
      const data = (await response.json()) as { data: Array<{ id: string }> };

      // Předpokládáme, že mcp-agent vrátí podobnou strukturu jako OpenAI API
      return data.data.map((model) => ({
        name: model.id,
        label: `MCP Agent - ${model.id}`, // Pro lepší identifikaci v UI
        provider: this.name,
        maxTokenAllowed: 8000, // Nebo jiná hodnota, kterou víte, že Gemini podporuje
      }));
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

    let baseUrl = this.config.baseUrl; // Změněno zde

    if (!baseUrl) {
      throw new Error(`Missing base URL for ${this.name} provider`);
    }

    const isDocker = process?.env?.RUNNING_IN_DOCKER === 'true' || serverEnv?.RUNNING_IN_DOCKER === 'true';

    if (typeof window === 'undefined') {
      // Běží na serveru
      if (isDocker) {
          baseUrl = baseUrl.replace('localhost', 'host.docker.internal').replace('127.0.0.1', 'host.docker.internal');
      }
    }

    logger.debug('MCPAgent Base Url used: ', baseUrl);
    logger.debug(`Attempting to get model instance for: ${model} with base URL: ${baseUrl}`); // Nové logování

    // mcp-agent by měl emulovat OpenAI API, takže použijeme getOpenAILikeModel
    // API klíč není potřeba, protože mcp-agent má vlastní klíč k Gemini
    return getOpenAILikeModel(baseUrl, '', model);
  }
}
