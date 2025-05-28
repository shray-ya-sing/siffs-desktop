interface Window {
  electron: {
    getEnv: (key: string) => string | undefined;
  };
}
