import { createContext, useContext, useEffect, useState, type PropsWithChildren } from "react";

import { loadRuntimeConfig, type RuntimeConfig } from "./runtimeConfig";

const RuntimeConfigContext = createContext<RuntimeConfig | null>(null);

/**
 * Resolve `/config.json` uma vez e só então renderiza os filhos, para que
 * o roteador e as telas já nasçam sabendo se o ambiente tem Cognito.
 * Enquanto a configuração não chega, nada é renderizado.
 */
export function RuntimeConfigProvider({ children }: PropsWithChildren) {
  const [config, setConfig] = useState<RuntimeConfig | null>(null);

  useEffect(() => {
    let active = true;
    void loadRuntimeConfig().then((loaded) => {
      if (active) setConfig(loaded);
    });
    return () => {
      active = false;
    };
  }, []);

  if (!config) return null;
  return <RuntimeConfigContext.Provider value={config}>{children}</RuntimeConfigContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useRuntimeConfig() {
  const context = useContext(RuntimeConfigContext);
  if (!context) throw new Error("useRuntimeConfig deve ser usado dentro de RuntimeConfigProvider");
  return context;
}
