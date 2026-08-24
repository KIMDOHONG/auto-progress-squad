import { useState, type FormEvent } from "react";
import { SendIcon } from "../../components/Icons";
import { getVehicleTitle } from "../../lib/vehicle";
import type { AppView, VehicleProfile } from "../../types";

const VIEW_LABELS: Record<AppView, string> = {
  dashboard: "대시보드",
  maintenance: "유지보수",
  manual: "매뉴얼·리콜",
  planner: "주행 에너지 플래너",
  "used-car": "중고차 분석",
};

interface Message { id: string; role: "assistant" | "user"; text: string; }
interface ChatPanelProps { vehicle: VehicleProfile; view: AppView; }

export function ChatPanel({ vehicle, view }: ChatPanelProps) {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([
    { id: "welcome", role: "assistant", text: "활성 차량과 현재 화면을 기준으로 도와드릴게요." },
  ]);

  function sendMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = input.trim();
    if (!text) return;
    setMessages((current) => [
      ...current,
      { id: crypto.randomUUID(), role: "user", text },
      { id: crypto.randomUUID(), role: "assistant", text: `${getVehicleTitle(vehicle)} · ${VIEW_LABELS[view]} 문맥을 확인했습니다. 현재는 UI 데모 응답이며 AI 모델은 다음 단계에서 연결합니다.` },
    ]);
    setInput("");
  }

  return (
    <aside className="chat-panel">
      <header><div><span className="online-dot" /><strong>AI 코파일럿</strong></div><span className="context-label">{vehicle.nickname}</span></header>
      <div className="chat-context"><span>{VIEW_LABELS[view]}</span><strong>{getVehicleTitle(vehicle)}</strong></div>
      <div className="messages" aria-live="polite">{messages.map((message) => <p key={message.id} className={`message ${message.role}`}>{message.text}</p>)}</div>
      <form className="chat-form" onSubmit={sendMessage}>
        <label className="sr-only" htmlFor="chat-input">AI 코파일럿에게 메시지 보내기</label>
        <input id="chat-input" value={input} onChange={(event) => setInput(event.target.value)} placeholder="차량에 대해 질문하세요" />
        <button type="submit" aria-label="메시지 전송"><SendIcon /></button>
      </form>
    </aside>
  );
}
