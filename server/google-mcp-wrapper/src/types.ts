export type JsonRpcRequest = {
  jsonrpc: "2.0";
  id?: string | number | null;
  method: string;
  params?: unknown;
};

export type JsonRpcError = {
  code: number;
  message: string;
  data?: unknown;
};

export type JsonRpcResponse = {
  jsonrpc: "2.0";
  id?: string | number | null;
  result?: unknown;
  error?: JsonRpcError;
};

export type Policy = {
  allowedTools: string[];
  deniedNamePatterns: string[];
  maxResultsDefault: number;
  gmail: {
    maxResults: number;
  };
  calendar: {
    maxDaysRange: number;
  };
  drive: {
    allowedFolderIds: string[];
  };
};
