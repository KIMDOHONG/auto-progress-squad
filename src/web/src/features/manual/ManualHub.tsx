import { useEffect, useState, type FormEvent } from "react";
import { BookIcon } from "../../components/Icons";
import { BMW_DRIVER_GUIDE, getCatalogManualAdapterId, getManualBrand, getVehicleManual, MANUAL_BRANDS } from "../../lib/manual";
import { getApiManualIngestion, retryApiManualIngestion, searchApiManual, VehicleApiError } from "../../lib/vehicleApi";
import { getVehicleTitle } from "../../lib/vehicle";
import type { VehicleSyncStatus } from "../../hooks/useVehicleProfiles";
import type { CatalogManualAdapterId, ManualIngestionStatus, ManualSearchResult, VehicleProfile } from "../../types";

interface ManualHubProps {
  vehicle: VehicleProfile;
  syncStatus: VehicleSyncStatus;
  onAttachManualAdapter?: (
    vehicleId: string,
    adapterId: CatalogManualAdapterId,
  ) => Promise<VehicleProfile>;
}

const EXTERNAL_LINK_PROPS = {
  target: "_blank",
  rel: "noreferrer noopener",
} as const;

function ManualVehicleVisual({ imageUrl, label }: { imageUrl?: string; label: string }) {
  const [failed, setFailed] = useState(false);

  useEffect(() => setFailed(false), [imageUrl]);

  if (!imageUrl || failed) return <BookIcon className="heading-mark" />;
  return (
    <div className="manual-vehicle-visual">
      <img src={imageUrl} alt={`${label} 공식 차량 이미지`} onError={() => setFailed(true)} />
      <span>제조사 공식 이미지</span>
    </div>
  );
}

function localIngestionStatus(vehicle: VehicleProfile): ManualIngestionStatus {
  return {
    vehicleId: vehicle.id,
    status: "unavailable",
    attemptCount: 0,
    canSearch: false,
  };
}

export function ManualHub({ vehicle, syncStatus, onAttachManualAdapter }: ManualHubProps) {
  const manual = getVehicleManual(vehicle);
  const brand = getManualBrand(vehicle.manufacturer);
  const catalogAdapterId = getCatalogManualAdapterId(vehicle.manufacturer);
  const requiresVin = vehicle.manufacturer.trim().toLocaleUpperCase("ko-KR") === "BMW";
  const [ingestion, setIngestion] = useState<ManualIngestionStatus>(() => localIngestionStatus(vehicle));
  const [retrying, setRetrying] = useState(false);
  const [question, setQuestion] = useState("");
  const [searching, setSearching] = useState(false);
  const [searchResult, setSearchResult] = useState<ManualSearchResult | null>(null);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [linking, setLinking] = useState(false);
  const [linkNotice, setLinkNotice] = useState<string | null>(null);

  useEffect(() => {
    setLinking(false);
    setLinkNotice(null);
  }, [vehicle.id]);

  useEffect(() => {
    let cancelled = false;
    setQuestion("");
    setSearchResult(null);
    setSearchError(null);
    if (!manual || syncStatus.mode !== "api" || !syncStatus.apiBaseUrl) {
      setIngestion(localIngestionStatus(vehicle));
      return;
    }
    setIngestion({ vehicleId: vehicle.id, status: "pending", attemptCount: 0, canSearch: false });
    void getApiManualIngestion(syncStatus.apiBaseUrl, vehicle.id)
      .then((next) => { if (!cancelled) setIngestion(next); })
      .catch(() => {
        if (!cancelled) setIngestion({
          vehicleId: vehicle.id,
          status: "failed",
          attemptCount: 0,
          failureMessage: "서버에서 문서 준비 상태를 확인하지 못했습니다.",
          canSearch: false,
        });
      });
    return () => { cancelled = true; };
  }, [manual?.projectCode, syncStatus.apiBaseUrl, syncStatus.mode, vehicle.id]);

  const retryIngestion = async () => {
    if (!syncStatus.apiBaseUrl) return;
    setRetrying(true);
    try {
      setIngestion(await retryApiManualIngestion(syncStatus.apiBaseUrl, vehicle.id));
    } catch {
      setIngestion((current) => ({
        ...current,
        status: "failed",
        failureMessage: "문서 준비 재시도 요청에 실패했습니다.",
        canSearch: false,
      }));
    } finally {
      setRetrying(false);
    }
  };

  const submitManualSearch = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const normalizedQuestion = question.trim();
    if (!syncStatus.apiBaseUrl || normalizedQuestion.length < 2 || !ingestion.canSearch) return;
    setSearching(true);
    setSearchError(null);
    try {
      setSearchResult(await searchApiManual(syncStatus.apiBaseUrl, vehicle.id, normalizedQuestion));
    } catch (error) {
      setSearchResult(null);
      setSearchError(error instanceof Error ? error.message : "매뉴얼을 검색하지 못했습니다.");
    } finally {
      setSearching(false);
    }
  };

  const attachCatalogManual = async () => {
    if (!catalogAdapterId || !onAttachManualAdapter) return;
    setLinking(true);
    setLinkNotice(null);
    try {
      await onAttachManualAdapter(vehicle.id, catalogAdapterId);
      setLinkNotice("승인된 차명·연식·세대 매뉴얼을 차량 프로필에 연결했습니다.");
    } catch (error) {
      if (error instanceof VehicleApiError && error.code === "manual_generation_required") {
        setLinkNotice("같은 차명과 연식에 여러 세대가 있어 세대 선택 기능이 필요합니다.");
      } else if (error instanceof VehicleApiError && error.code === "manual_mapping_not_found") {
        setLinkNotice("정확히 일치하는 승인 매뉴얼 매핑이 없습니다.");
      } else {
        setLinkNotice(error instanceof Error ? error.message : "승인 매뉴얼을 연결하지 못했습니다.");
      }
    } finally {
      setLinking(false);
    }
  };

  const ingestionCopy = !manual
    ? { label: "공식 문서 확인 필요", title: "AI 매뉴얼 검색 대기", detail: "정확한 차종·연식의 공식 문서가 확인되어야 준비를 시작할 수 있습니다." }
    : syncStatus.mode !== "api"
      ? { label: "서버 연결 필요", title: "AI 매뉴얼 검색 대기", detail: "공개 데모는 PDF를 저장하지 않습니다. FastAPI 서버에 연결하면 문서 준비 상태를 확인할 수 있습니다." }
      : ingestion.status === "ready"
        ? { label: "사용 가능", title: "AI 매뉴얼 검색 준비 완료", detail: "이 차량과 정확히 일치하는 설명서 검색 인덱스가 준비되었습니다." }
        : ingestion.status === "failed"
          ? { label: "준비 실패", title: "취급설명서를 준비하지 못했습니다", detail: ingestion.failureMessage ?? "서버 기록을 확인한 뒤 다시 시도해 주세요." }
          : ingestion.status === "unavailable"
            ? { label: "검색 미연결", title: "AI 매뉴얼 검색 대기", detail: "공식 링크는 연결됐지만 장별 PDF 검색 인덱스는 아직 구성되지 않았습니다." }
          : { label: "확인 중", title: "취급설명서를 확인 중입니다", detail: "정확한 공식 원문을 서버에서 준비하기 전까지 RAG 검색은 잠겨 있습니다." };

  return (
    <section className="page-section manual-page">
      <div className="page-heading compact">
        <div>
          <p className="section-caption">공식 원문 연결</p>
          <h1>차량 취급설명서</h1>
          <p>{getVehicleTitle(vehicle)}에 맞는 제조사 공식 문서를 안내합니다.</p>
        </div>
        <ManualVehicleVisual imageUrl={manual?.imageUrl} label={getVehicleTitle(vehicle)} />
      </div>

      <article className={`manual-current ${manual ? "is-ready" : "is-pending"}`}>
        <div className="manual-current-copy">
          <span className="manual-status">{manual ? "차량·연식 확인됨" : requiresVin ? "VIN 확인 필요" : "차량 매칭 필요"}</span>
          <h2>{getVehicleTitle(vehicle)}</h2>
          {manual ? (
            <>
              <p>{manual.label} 공식 취급설명서의 <strong>{manual.generation ?? manual.projectCode} · {manual.modelYear}</strong> 문서로 연결합니다.</p>
              {manual.manualTitle ? <p className="manual-note">{manual.manualTitle}</p> : null}
              <p className="manual-note">디지털 설명서, 경고등·심벌, PDF 열기·다운로드는 제조사 페이지에서 선택할 수 있습니다.</p>
            </>
          ) : requiresVin ? (
            <p>{getVehicleTitle(vehicle)}의 정확한 취급설명서는 BMW Driver&apos;s Guide에서 17자리 VIN으로 차량을 식별한 뒤 연결합니다. 다른 BMW 차량의 문서를 대신 연결하지 않습니다.</p>
          ) : (
            <p>이 차량의 연식·세대·프로젝트 코드가 아직 등록되지 않았습니다. 유사 차종 문서를 자동으로 연결하지 않습니다.</p>
          )}
        </div>
        <div className="manual-actions">
          {manual ? <a className="primary-button" href={manual.manualUrl} {...EXTERNAL_LINK_PROPS}>공식 취급설명서 열기 <span aria-hidden="true">↗</span></a> : null}
          {requiresVin ? <a className="primary-button" href={BMW_DRIVER_GUIDE.homeUrl} {...EXTERNAL_LINK_PROPS}>BMW Driver&apos;s Guide 열기 <span aria-hidden="true">↗</span></a> : null}
          {brand ? <a className="secondary-button" href={brand.homeUrl} {...EXTERNAL_LINK_PROPS}>{brand.label} 차량 찾기 <span aria-hidden="true">↗</span></a> : null}
          {!manual && catalogAdapterId && syncStatus.mode === "api" && onAttachManualAdapter ? (
            <button className="secondary-button" type="button" disabled={linking} onClick={() => void attachCatalogManual()}>
              {linking ? "승인 매핑 확인 중" : "승인 매뉴얼 연결"}
            </button>
          ) : null}
        </div>
      </article>
      {linkNotice ? <p className="manual-link-notice" role="status">{linkNotice}</p> : null}

      <div className="manual-grid">
        <section className="manual-source-section" aria-labelledby="manual-brand-title">
          <div className="manual-section-heading">
            <div><p className="section-caption">제조사별 공식 문서</p><h2 id="manual-brand-title">차량 찾기</h2></div>
            <span>새 탭에서 열림</span>
          </div>
          <div className="manual-brand-list">
            {MANUAL_BRANDS.map((source) => (
              <a key={source.manufacturer} href={source.homeUrl} {...EXTERNAL_LINK_PROPS}>
                <span>{source.label}</span>
                <small>차종·연식 선택</small>
                <strong aria-hidden="true">↗</strong>
              </a>
            ))}
            <a href={BMW_DRIVER_GUIDE.homeUrl} {...EXTERNAL_LINK_PROPS}>
              <span>{BMW_DRIVER_GUIDE.label}</span>
              <small>VIN으로 차량 식별</small>
              <strong aria-hidden="true">↗</strong>
            </a>
          </div>
        </section>

        <aside className={`rag-next-step ingestion-${ingestion.status}`} aria-live="polite">
          <div className="ingestion-heading">
            <p className="section-caption">매뉴얼 검색 준비</p>
            <span>{ingestionCopy.label}</span>
          </div>
          <h2>{ingestionCopy.title}</h2>
          <p>{ingestionCopy.detail}</p>
          <ul>
            <li>상태: {ingestion.status}</li>
            <li>검색: {ingestion.canSearch ? "사용 가능" : "준비 완료 전 차단"}</li>
            <li>원칙: 다른 연식·세대·N 모델 문서 혼용 금지</li>
          </ul>
          {ingestion.status === "failed" && syncStatus.mode === "api" ? (
            <button className="secondary-button ingestion-retry" type="button" disabled={retrying} onClick={() => void retryIngestion()}>
              {retrying ? "재시도 요청 중" : "문서 준비 재시도"}
            </button>
          ) : null}
        </aside>
      </div>

      {ingestion.canSearch && syncStatus.apiBaseUrl ? (
        <section className="manual-search-panel" aria-labelledby="manual-search-title">
          <div className="manual-section-heading">
            <div>
              <p className="section-caption">차량별 공식 문서 검색</p>
              <h2 id="manual-search-title">취급설명서 질문</h2>
            </div>
            <span>현재 차량 문서만 검색</span>
          </div>
          <form className="manual-search-form" onSubmit={(event) => void submitManualSearch(event)}>
            <label htmlFor="manual-search-question">설명서에서 찾을 내용</label>
            <div>
              <input
                id="manual-search-question"
                value={question}
                minLength={2}
                maxLength={500}
                placeholder="예: 타이어 공기압은 어디서 확인해?"
                onChange={(event) => setQuestion(event.target.value)}
              />
              <button className="primary-button" type="submit" disabled={searching || question.trim().length < 2}>
                {searching ? "검색 중" : "설명서 검색"}
              </button>
            </div>
          </form>
          {searchError ? <p className="manual-search-error" role="alert">{searchError}</p> : null}
          {searchResult ? (
            <div className="manual-search-result" aria-live="polite">
              <strong>{searchResult.answer}</strong>
              {searchResult.sources.length > 0 ? (
                <ol>
                  {searchResult.sources.map((source, index) => (
                    <li key={`${source.sourceUrl}-${source.page ?? "none"}-${index}`}>
                      <div>
                        <a href={source.sourceUrl} {...EXTERNAL_LINK_PROPS}>{source.documentName}</a>
                        <span>{source.page ? `${source.page}쪽` : "페이지 정보 없음"}{source.section ? ` · ${source.section}` : ""}</span>
                      </div>
                      <p>{source.excerpt}</p>
                    </li>
                  ))}
                </ol>
              ) : <p>검색어를 바꾸거나 제조사 원문에서 직접 확인해 주세요.</p>}
            </div>
          ) : null}
        </section>
      ) : null}

      <div className="manual-embed-note">
        <strong>공식 페이지를 내부에 띄우지 않는 이유</strong>
        <span>제조사 사이트가 다른 도메인의 iframe 표시를 제한하므로, 기능이 깨지지 않는 공식 새 탭 연결 방식을 사용합니다.</span>
      </div>
    </section>
  );
}
