export interface SSEEvent {
  event: string;
  data: unknown;
}

/**
 * Parse a text/event-stream response body into events. Data is JSON
 * (the backend JSON-encodes every frame; see server/utils/streaming_utils.py).
 */
export async function* readSSE(response: Response): AsyncGenerator<SSEEvent> {
  if (!response.body) throw new Error("Response has no body");
  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += value;
    let boundary: number;
    while ((boundary = buffer.indexOf("\n\n")) !== -1) {
      const frame = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      let event = "message";
      const data: string[] = [];
      for (const line of frame.split("\n")) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        else if (line.startsWith("data:")) data.push(line.slice(5).trimStart());
      }
      if (data.length) yield { event, data: JSON.parse(data.join("\n")) };
    }
  }
}
