import { useState, type FormEvent } from "react";
import { SendIcon } from "../../components/Icons";
import {
  parseVehicleRegistration,
  searchOfficialVehicles,
  toManualMetadata,
  type OfficialVehicleCandidate,
} from "../../lib/officialVehicle";
import { FUEL_GRADE_LABELS, POWERTRAIN_LABELS, getVehicleTitle } from "../../lib/vehicle";
import type { AppView, FuelGrade, Powertrain, VehicleProfile } from "../../types";

const VIEW_LABELS: Record<AppView, string> = {
  dashboard: "대시보드",
  maintenance: "유지보수",
  manual: "매뉴얼·리콜",
  planner: "주행 에너지 플래너",
  "used-car": "중고차 분석",
};

interface RegistrationDraft {
  candidate: OfficialVehicleCandidate;
  nickname: string;
  powertrain: Powertrain;
  fuelGrade?: FuelGrade;
}

interface TextMessage {
  id: string;
  kind: "text";
  role: "assistant" | "user";
  text: string;
}

interface LinkMessage {
  id: string;
  kind: "link";
  role: "assistant";
  text: string;
  href: string;
  label: string;
}

interface CandidateMessage {
  id: string;
  kind: "candidates";
  role: "assistant";
  text: string;
  candidates: OfficialVehicleCandidate[];
}

interface ConfirmationMessage {
  id: string;
  kind: "confirmation";
  role: "assistant";
  candidate: OfficialVehicleCandidate;
}

interface ReplacementChoiceMessage {
  id: string;
  kind: "replacement-choice";
  role: "assistant";
  draft: RegistrationDraft;
}

interface ReplacementConfirmationMessage {
  id: string;
  kind: "replacement-confirmation";
  role: "assistant";
  draft: RegistrationDraft;
  previousVehicle: VehicleProfile;
}

interface DeletionChoiceMessage {
  id: string;
  kind: "deletion-choice";
  role: "assistant";
  vehicles: VehicleProfile[];
}

interface DeletionConfirmationMessage {
  id: string;
  kind: "deletion-confirmation";
  role: "assistant";
  target: VehicleProfile;
}

type Message = TextMessage | LinkMessage | CandidateMessage | ConfirmationMessage
  | ReplacementChoiceMessage | ReplacementConfirmationMessage
  | DeletionChoiceMessage | DeletionConfirmationMessage;

interface ChatPanelProps {
  vehicle: VehicleProfile;
  vehicles: VehicleProfile[];
  view: AppView;
  onAddVehicle: (vehicle: VehicleProfile) => Promise<boolean>;
  onReplaceVehicle: (vehicleId: string, replacement: VehicleProfile) => Promise<void>;
  onDeleteVehicle: (vehicleId: string) => Promise<void>;
}

interface VehicleConfirmationProps {
  candidate: OfficialVehicleCandidate;
  isFull: boolean;
  disabled: boolean;
  onCancel: () => void;
  onConfirm: (draft: RegistrationDraft) => void;
}

function normalize(value: string): string {
  return value.toLocaleUpperCase("ko-KR").replace(/[^0-9A-Z가-힣]/g, "");
}

function createVehicleProfile(draft: RegistrationDraft): VehicleProfile {
  return {
    id: crypto.randomUUID(),
    nickname: draft.nickname.trim() || `${draft.candidate.modelName} ${draft.candidate.modelYear}`,
    manufacturer: draft.candidate.manufacturer,
    model: draft.candidate.modelName,
    modelYear: draft.candidate.modelYear,
    powertrain: draft.powertrain,
    ...(draft.fuelGrade ? { fuelGrade: draft.fuelGrade } : {}),
    manual: toManualMetadata(draft.candidate),
  };
}

function parseDeletionQuery(text: string): string | null {
  if (!/(삭제|지워|제거)/.test(text)) return null;
  return text
    .replace(/(프로필|차량|삭제해\s*줘|삭제해주세요|삭제|지워\s*줘|지워주세요|지워|제거해\s*줘|제거)/g, " ")
    .replace(/[,.!?()[\]{}]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function findVehicleMatches(vehicles: VehicleProfile[], query: string): VehicleProfile[] {
  const target = normalize(query);
  if (!target) return [];
  const exact = vehicles.filter((item) => [item.nickname, item.model, getVehicleTitle(item)]
    .some((value) => normalize(value) === target));
  if (exact.length) return exact;
  return vehicles.filter((item) => [item.nickname, item.model, getVehicleTitle(item)]
    .some((value) => normalize(value).includes(target) || target.includes(normalize(value))));
}

function VehicleCandidateCards({ candidates, onSelect }: { candidates: OfficialVehicleCandidate[]; onSelect: (candidate: OfficialVehicleCandidate) => void }) {
  return (
    <div className="vehicle-candidate-list">
      {candidates.map((candidate) => (
        <button key={candidate.id} type="button" className="vehicle-candidate-card" aria-label={`${candidate.modelYear} ${candidate.modelName} ${candidate.projectCode} 선택`} onClick={() => onSelect(candidate)}>
          <img src={candidate.imageUrl} alt={`${candidate.label} ${candidate.modelName} ${candidate.projectCode}`} loading="lazy" />
          <span>{candidate.label} · {candidate.modelYear}</span>
          <strong>{candidate.modelName}</strong>
          <small>프로젝트 코드 {candidate.projectCode}</small>
        </button>
      ))}
    </div>
  );
}

function VehicleConfirmation({ candidate, isFull, disabled, onCancel, onConfirm }: VehicleConfirmationProps) {
  const [nickname, setNickname] = useState(`${candidate.modelName} ${candidate.modelYear}`);
  const [powertrain, setPowertrain] = useState<Powertrain>(candidate.suggestedPowertrain);
  const [fuelGrade, setFuelGrade] = useState<FuelGrade>(candidate.suggestedPowertrain === "diesel" ? "diesel" : "regular");

  return (
    <div className="vehicle-confirmation">
      <img src={candidate.imageUrl} alt={`${candidate.label} ${candidate.modelName}`} />
      <div><span>선택한 공식 차량</span><strong>{candidate.modelName} · {candidate.modelYear}</strong><small>{candidate.projectCode} · {candidate.fuel}</small></div>
      <label>별명<input value={nickname} onChange={(event) => setNickname(event.target.value)} /></label>
      <label>동력원<select value={powertrain} onChange={(event) => setPowertrain(event.target.value as Powertrain)}>{Object.entries(POWERTRAIN_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
      {powertrain === "gasoline" || powertrain === "diesel" || powertrain === "hybrid" ? (
        <label>지정 연료<select value={fuelGrade} onChange={(event) => setFuelGrade(event.target.value as FuelGrade)}>{Object.entries(FUEL_GRADE_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
      ) : null}
      {candidate.fuel === "ICE" ? <p>공식 설명서 데이터는 내연기관 종류를 세분화하지 않을 수 있습니다. 실제 차량의 동력원과 지정 연료를 확인해 주세요.</p> : null}
      {isFull ? <p>현재 프로필이 3대이고 최대 3대까지 등록할 수 있습니다. 계속하면 기존 프로필 중 교체할 차량을 선택합니다.</p> : null}
      <div className="chat-confirm-actions">
        <button type="button" className="primary-button" disabled={disabled} onClick={() => onConfirm({ candidate, nickname, powertrain, fuelGrade: powertrain === "electric" || powertrain === "hydrogen" ? undefined : fuelGrade })}>{isFull ? "기존 차량 교체 후 등록" : "프로필 등록"}</button>
        <button type="button" className="secondary-button" disabled={disabled} onClick={onCancel}>취소</button>
      </div>
    </div>
  );
}

function ProfileChoiceList({ vehicles, actionLabel, disabled, onSelect }: { vehicles: VehicleProfile[]; actionLabel: string; disabled: boolean; onSelect: (vehicle: VehicleProfile) => void }) {
  return (
    <div className="profile-choice-list">
      {vehicles.map((item) => (
        <button key={item.id} type="button" disabled={disabled} onClick={() => onSelect(item)}>
          {item.manual?.imageUrl ? <img src={item.manual.imageUrl} alt="" loading="lazy" /> : null}
          <span><strong>{item.nickname}</strong><small>{getVehicleTitle(item)}</small></span>
          <em>{actionLabel}</em>
        </button>
      ))}
    </div>
  );
}

export function ChatPanel({ vehicle, vehicles, view, onAddVehicle, onReplaceVehicle, onDeleteVehicle }: ChatPanelProps) {
  const [input, setInput] = useState("");
  const [isWorking, setIsWorking] = useState(false);
  const [handledMessageIds, setHandledMessageIds] = useState<string[]>([]);
  const [messages, setMessages] = useState<Message[]>([
    { id: "welcome", kind: "text", role: "assistant", text: "활성 차량과 현재 화면을 기준으로 도와드릴게요. ‘2020 K5 등록’ 또는 ‘스팅어 프로필 삭제’처럼 입력할 수 있습니다." },
  ]);

  function appendMessage(message: Message) {
    setMessages((current) => [...current, message]);
  }

  function handleOnce(messageId: string): boolean {
    if (handledMessageIds.includes(messageId)) return false;
    setHandledMessageIds((current) => [...current, messageId]);
    return true;
  }

  function requestDeletion(query: string) {
    if (vehicles.length === 1) {
      appendMessage({ id: crypto.randomUUID(), kind: "text", role: "assistant", text: "마지막 차량 프로필은 삭제할 수 없습니다. 다른 차량을 먼저 등록한 뒤 다시 요청해 주세요." });
      return;
    }
    const matches = findVehicleMatches(vehicles, query);
    if (!matches.length) {
      appendMessage({ id: crypto.randomUUID(), kind: "text", role: "assistant", text: `‘${query || "입력한 차량"}’과 일치하는 등록 프로필을 찾지 못했습니다. 별명 또는 차명을 확인해 주세요.` });
      return;
    }
    if (matches.length === 1) {
      appendMessage({ id: crypto.randomUUID(), kind: "deletion-confirmation", role: "assistant", target: matches[0] });
      return;
    }
    appendMessage({ id: crypto.randomUUID(), kind: "deletion-choice", role: "assistant", vehicles: matches });
  }

  async function sendMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = input.trim();
    if (!text || isWorking) return;
    appendMessage({ id: crypto.randomUUID(), kind: "text", role: "user", text });
    setInput("");

    const deletionQuery = parseDeletionQuery(text);
    if (deletionQuery !== null) {
      requestDeletion(deletionQuery);
      return;
    }

    if (/리콜/.test(text)) {
      appendMessage({ id: crypto.randomUUID(), kind: "text", role: "assistant", text: "리콜 조회 기능은 아직 공식 데이터와 연결되지 않았습니다. 현재 차량 정보를 근거 없이 추정하지 않고, 제조사·자동차리콜센터 연결 단계에서 구현하겠습니다." });
      return;
    }

    const request = parseVehicleRegistration(text);
    if (!request) {
      appendMessage({ id: crypto.randomUUID(), kind: "text", role: "assistant", text: `${getVehicleTitle(vehicle)} · ${VIEW_LABELS[view]} 문맥을 확인했습니다. 차량 등록은 제조사(선택), 차명, 네 자리 연식을 함께 입력해 주세요.` });
      return;
    }

    if (request.manufacturerSupport === "official-link" && request.manufacturerManualUrl) {
      appendMessage({ id: crypto.randomUUID(), kind: "link", role: "assistant", text: `${request.manufacturer} ${request.modelQuery} · ${request.modelYear}로 인식했습니다. ${request.manufacturer} 공식 설명서 페이지는 확인했지만, 연식·세부 모델 자동 식별 연결은 아직 준비 중입니다. 지금은 차량 관리에서 직접 등록하고 공식 페이지에서 연식을 확인해 주세요.`, href: request.manufacturerManualUrl, label: `${request.manufacturer} 공식 취급설명서 열기` });
      return;
    }

    if (request.manufacturerSupport === "unsupported") {
      appendMessage({ id: crypto.randomUUID(), kind: "text", role: "assistant", text: `${request.manufacturer} ${request.modelQuery} · ${request.modelYear}로 인식했습니다. 현재 자동 식별은 현대·기아·제네시스 공식 데이터만 연결되어 있으며, ${request.manufacturer} 공식 설명서는 아직 조회하지 않았습니다. 차량 관리에서 직접 등록할 수 있습니다.` });
      return;
    }

    setIsWorking(true);
    try {
      const result = await searchOfficialVehicles(request);
      if (!result.candidates.length) {
        const yearGuide = result.availableYears?.length ? ` 확인 가능한 연식: ${result.availableYears.slice(0, 8).join(", ")}` : "";
        const source = request.manufacturer ? `${request.manufacturer} 공식 취급설명서 데이터에서` : "현재 연결된 현대·기아·제네시스 공식 취급설명서 데이터에서";
        appendMessage({ id: crypto.randomUUID(), kind: "text", role: "assistant", text: `${source} ${request.modelYear}년식 ‘${request.modelQuery}’ 차량을 확인하지 못했습니다.${yearGuide}` });
        return;
      }
      const correction = result.correctedModelName ? `‘${request.modelQuery}’ 입력과 가까운 ‘${result.correctedModelName}’ 후보입니다. ` : "";
      const ambiguity = result.candidates.length > 1 ? "같은 연식에 여러 세대가 있어 차량 이미지를 보고 선택해 주세요." : "공식 차량 이미지를 확인한 뒤 선택해 주세요.";
      appendMessage({ id: crypto.randomUUID(), kind: "candidates", role: "assistant", text: `${correction}${ambiguity}`, candidates: result.candidates });
    } catch {
      appendMessage({ id: crypto.randomUUID(), kind: "text", role: "assistant", text: "연결된 제조사 공식 차량 정보를 불러오지 못했습니다. 잠시 후 다시 시도하거나 차량 관리에서 직접 입력해 주세요." });
    } finally {
      setIsWorking(false);
    }
  }

  function selectCandidate(candidate: OfficialVehicleCandidate) {
    appendMessage({ id: crypto.randomUUID(), kind: "confirmation", role: "assistant", candidate });
  }

  async function continueRegistration(messageId: string, draft: RegistrationDraft) {
    if (!handleOnce(messageId)) return;
    if (vehicles.length >= 3) {
      appendMessage({ id: crypto.randomUUID(), kind: "replacement-choice", role: "assistant", draft });
      return;
    }
    setIsWorking(true);
    try {
      const added = await onAddVehicle(createVehicleProfile(draft));
      appendMessage({ id: crypto.randomUUID(), kind: "text", role: "assistant", text: added ? `${draft.candidate.manufacturer} ${draft.candidate.modelName} · ${draft.candidate.modelYear} (${draft.candidate.projectCode}) 프로필을 등록하고 활성 차량으로 변경했습니다.` : "등록 가능한 차량 수가 변경되었습니다. 기존 차량 교체 방식으로 다시 진행해 주세요." });
    } catch (caught) {
      appendMessage({ id: crypto.randomUUID(), kind: "text", role: "assistant", text: caught instanceof Error ? caught.message : "차량 프로필을 저장하지 못했습니다." });
    } finally {
      setIsWorking(false);
    }
  }

  function chooseReplacement(messageId: string, draft: RegistrationDraft, previousVehicle: VehicleProfile) {
    if (!handleOnce(messageId)) return;
    appendMessage({ id: crypto.randomUUID(), kind: "replacement-confirmation", role: "assistant", draft, previousVehicle });
  }

  async function confirmReplacement(messageId: string, draft: RegistrationDraft, previousVehicle: VehicleProfile) {
    if (!handleOnce(messageId)) return;
    setIsWorking(true);
    try {
      await onReplaceVehicle(previousVehicle.id, createVehicleProfile(draft));
      appendMessage({ id: crypto.randomUUID(), kind: "text", role: "assistant", text: `${previousVehicle.nickname} 프로필을 ${draft.candidate.manufacturer} ${draft.candidate.modelName} · ${draft.candidate.modelYear} 프로필로 교체하고 활성화했습니다.` });
    } catch (caught) {
      appendMessage({ id: crypto.randomUUID(), kind: "text", role: "assistant", text: caught instanceof Error ? caught.message : "차량 프로필을 교체하지 못했습니다." });
    } finally {
      setIsWorking(false);
    }
  }

  function chooseDeletion(messageId: string, target: VehicleProfile) {
    if (!handleOnce(messageId)) return;
    appendMessage({ id: crypto.randomUUID(), kind: "deletion-confirmation", role: "assistant", target });
  }

  async function confirmDeletion(messageId: string, target: VehicleProfile) {
    if (!handleOnce(messageId)) return;
    setIsWorking(true);
    try {
      await onDeleteVehicle(target.id);
      appendMessage({ id: crypto.randomUUID(), kind: "text", role: "assistant", text: `${target.nickname} · ${getVehicleTitle(target)} 프로필을 삭제했습니다.` });
    } catch (caught) {
      appendMessage({ id: crypto.randomUUID(), kind: "text", role: "assistant", text: caught instanceof Error ? caught.message : "차량 프로필을 삭제하지 못했습니다." });
    } finally {
      setIsWorking(false);
    }
  }

  function cancelAction(messageId: string, text: string) {
    if (!handleOnce(messageId)) return;
    appendMessage({ id: crypto.randomUUID(), kind: "text", role: "assistant", text });
  }

  return (
    <aside className="chat-panel">
      <header><div><span className="online-dot" /><strong>AI 코파일럿</strong></div><span className="context-label">{vehicle.nickname}</span></header>
      <div className="chat-context"><span>{VIEW_LABELS[view]}</span><strong>{getVehicleTitle(vehicle)}</strong></div>
      <div className="messages" aria-live="polite">
        {messages.map((message) => {
          const handled = handledMessageIds.includes(message.id);
          if (message.kind === "candidates") return <div key={message.id} className="message rich-message"><p>{message.text}</p><VehicleCandidateCards candidates={message.candidates} onSelect={selectCandidate} /></div>;
          if (message.kind === "confirmation") return <div key={message.id} className="message rich-message"><VehicleConfirmation candidate={message.candidate} isFull={vehicles.length >= 3} disabled={isWorking || handled} onCancel={() => cancelAction(message.id, "차량 등록을 취소했습니다.")} onConfirm={(draft) => void continueRegistration(message.id, draft)} /></div>;
          if (message.kind === "link") return <div key={message.id} className="message rich-message"><p>{message.text}</p><a className="chat-official-link" href={message.href} target="_blank" rel="noreferrer">{message.label} ↗</a></div>;
          if (message.kind === "replacement-choice") return <div key={message.id} className="message rich-message"><p>현재 프로필이 3대이고 최대 3대까지 등록할 수 있습니다. 기존 프로필 중 하나를 교체하고 추가하시겠습니까?</p><ProfileChoiceList vehicles={vehicles} actionLabel="교체" disabled={isWorking || handled} onSelect={(item) => chooseReplacement(message.id, message.draft, item)} /></div>;
          if (message.kind === "replacement-confirmation") return <div key={message.id} className="message rich-message"><p><strong>{message.previousVehicle.nickname}</strong> 프로필을 삭제하고 <strong>{message.draft.candidate.modelName} · {message.draft.candidate.modelYear}</strong> 차량을 등록할까요?</p><div className="chat-confirm-actions"><button type="button" className="primary-button" disabled={isWorking || handled} onClick={() => void confirmReplacement(message.id, message.draft, message.previousVehicle)}>삭제하고 등록</button><button type="button" className="secondary-button" disabled={isWorking || handled} onClick={() => cancelAction(message.id, "프로필 교체를 취소했습니다.")}>취소</button></div></div>;
          if (message.kind === "deletion-choice") return <div key={message.id} className="message rich-message"><p>삭제할 차량 프로필을 선택해 주세요.</p><ProfileChoiceList vehicles={message.vehicles} actionLabel="삭제" disabled={isWorking || handled} onSelect={(item) => chooseDeletion(message.id, item)} /></div>;
          if (message.kind === "deletion-confirmation") return <div key={message.id} className="message rich-message"><p><strong>{message.target.nickname} · {getVehicleTitle(message.target)}</strong> 프로필을 삭제할까요? 이 작업은 현재 브라우저 또는 연결된 차량 API에 반영됩니다.</p><div className="chat-confirm-actions"><button type="button" className="danger-button" disabled={isWorking || handled} onClick={() => void confirmDeletion(message.id, message.target)}>프로필 삭제</button><button type="button" className="secondary-button" disabled={isWorking || handled} onClick={() => cancelAction(message.id, "프로필 삭제를 취소했습니다.")}>취소</button></div></div>;
          return <p key={message.id} className={`message ${message.role}`}>{message.text}</p>;
        })}
        {isWorking ? <p className="message" role="status">요청을 안전하게 처리하고 있습니다…</p> : null}
      </div>
      <form className="chat-form" onSubmit={sendMessage}>
        <label className="sr-only" htmlFor="chat-input">AI 코파일럿에게 메시지 보내기</label>
        <input id="chat-input" value={input} disabled={isWorking} onChange={(event) => setInput(event.target.value)} placeholder="예: 2020 K5 등록" />
        <button type="submit" disabled={isWorking} aria-label="메시지 전송"><SendIcon /></button>
      </form>
    </aside>
  );
}
