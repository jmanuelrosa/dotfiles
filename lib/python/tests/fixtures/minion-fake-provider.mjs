import { appendFileSync, writeFileSync } from "node:fs";

function wait(delayMs, signal) {
  if (!delayMs || signal?.aborted) return Promise.resolve();
  return new Promise((resolve) => {
    const timer = setTimeout(resolve, delayMs);
    signal?.addEventListener("abort", () => {
      clearTimeout(timer);
      resolve();
    }, { once: true });
  });
}

function messageText(message) {
  if (!Array.isArray(message.content)) return String(message.content ?? "");
  return message.content
    .filter((block) => block.type === "text")
    .map((block) => block.text)
    .join("\n");
}

export function registerMinionFakeProvider(pi, ai, responses, observationPath) {
  const faux = ai.fauxProvider({
    provider: "minion-fake",
    api: "minion-fake",
    models: [{ id: "minion-fake", name: "Minion Fake" }],
    tokenSize: { min: 100000, max: 100000 },
  });
  faux.setResponses(responses.map((response, index) => async (context, options) => {
    appendFileSync(observationPath, `${JSON.stringify({
      index,
      sessionId: options?.sessionId,
      roles: context.messages.map((message) => message.role),
      systemMessages: context.messages.filter((message) => message.role === "system")
        .map((message) => [messageText(message), ...Object.values(message.sections ?? {}).filter(Boolean)].join("\n")),
      userMessages: context.messages.filter((message) => message.role === "user").map(messageText),
    })}\n`);
    await wait(response.delayMs, options?.signal);
    if (response.externalWrite) writeFileSync(response.externalWrite.path, response.externalWrite.content);
    if (response.tool) {
      return ai.fauxAssistantMessage(ai.fauxToolCall(response.tool.name, response.tool.arguments), { stopReason: "toolUse" });
    }
    if (response.report) {
      return ai.fauxAssistantMessage(ai.fauxToolCall("minion_report", response.report), { stopReason: "toolUse" });
    }
    return ai.fauxAssistantMessage(response.text ?? "No report");
  }));
  pi.registerProvider(faux.provider);
}
