export async function exerciseTools(session, calls) {
  const results = [];
  let turn = 0;
  session.agent.streamFunction = model => {
    const call = calls[turn++];
    const message = {
      role: "assistant",
      api: model.api,
      provider: model.provider,
      model: model.id,
      content: call
        ? [{ type: "toolCall", id: String(turn), name: call.name, arguments: call.input }]
        : [{ type: "text", text: "Probe finished" }],
      usage: {
        input: 0, output: 0, cacheRead: 0, cacheWrite: 0, totalTokens: 0,
        cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0 },
      },
      stopReason: call ? "toolUse" : "stop",
      timestamp: Date.now(),
    };
    return {
      async *[Symbol.asyncIterator]() {
        yield { type: "done", reason: message.stopReason, message };
      },
      result: async () => message,
    };
  };
  await session.modelRuntime.setRuntimeApiKey(session.model.provider, "offline-test-key");
  const unsubscribe = session.subscribe(event => {
    if (event.type === "tool_execution_end") {
      results.push({ name: event.toolName, isError: event.isError, result: event.result });
    }
  });
  try {
    await session.prompt("Execute the deterministic scratch-tool probe.");
    return { results };
  } finally {
    unsubscribe();
  }
}
