import { BookIcon } from "../../components/Icons";
import { getManualBrand, getVehicleManual, MANUAL_BRANDS } from "../../lib/manual";
import { getVehicleTitle } from "../../lib/vehicle";
import type { VehicleProfile } from "../../types";

interface ManualHubProps {
  vehicle: VehicleProfile;
}

const EXTERNAL_LINK_PROPS = {
  target: "_blank",
  rel: "noreferrer noopener",
} as const;

export function ManualHub({ vehicle }: ManualHubProps) {
  const manual = getVehicleManual(vehicle);
  const brand = getManualBrand(vehicle.manufacturer);
  const requiresVin = vehicle.manufacturer.trim().toLocaleUpperCase("ko-KR") === "BMW";

  return (
    <section className="page-section manual-page">
      <div className="page-heading compact">
        <div>
          <p className="section-caption">공식 원문 연결</p>
          <h1>차량 취급설명서</h1>
          <p>{getVehicleTitle(vehicle)}에 맞는 제조사 공식 문서를 안내합니다.</p>
        </div>
        <BookIcon className="heading-mark" />
      </div>

      <article className={`manual-current ${manual ? "is-ready" : "is-pending"}`}>
        <div className="manual-current-copy">
          <span className="manual-status">{manual ? "차량·연식 확인됨" : requiresVin ? "VIN 확인 필요" : "차량 매칭 필요"}</span>
          <h2>{getVehicleTitle(vehicle)}</h2>
          {manual ? (
            <>
              <p>{manual.label} 공식 취급설명서의 <strong>{manual.projectCode} · {manual.modelYear}</strong> 문서로 연결합니다.</p>
              <p className="manual-note">디지털 설명서, 경고등·심벌, PDF 열기·다운로드는 제조사 페이지에서 선택할 수 있습니다.</p>
            </>
          ) : requiresVin ? (
            <p>BMW 취급설명서는 VIN으로 차량을 식별한 뒤 연결합니다. 2021 G80 M3의 VIN을 확보하기 전까지 임의의 문서를 대신 연결하지 않습니다.</p>
          ) : (
            <p>이 차량의 연식·세대·프로젝트 코드가 아직 등록되지 않았습니다. 유사 차종 문서를 자동으로 연결하지 않습니다.</p>
          )}
        </div>
        <div className="manual-actions">
          {manual ? <a className="primary-button" href={manual.manualUrl} {...EXTERNAL_LINK_PROPS}>공식 취급설명서 열기 <span aria-hidden="true">↗</span></a> : null}
          {brand ? <a className="secondary-button" href={brand.homeUrl} {...EXTERNAL_LINK_PROPS}>{brand.label} 차량 찾기 <span aria-hidden="true">↗</span></a> : null}
        </div>
      </article>

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
          </div>
        </section>

        <aside className="rag-next-step">
          <p className="section-caption">다음 구현 단계</p>
          <h2>AI 매뉴얼 검색(RAG)</h2>
          <p>RAG는 질문과 관련된 설명서 부분을 먼저 찾은 뒤, 그 근거만 사용해 답변하고 문서 위치를 함께 보여주는 방식입니다.</p>
          <ul>
            <li>현재: 정확한 공식 원문으로 이동</li>
            <li>다음: PDF 텍스트 검색과 페이지 인용</li>
            <li>원칙: 다른 연식·세대·N 모델 문서 혼용 금지</li>
          </ul>
        </aside>
      </div>

      <div className="manual-embed-note">
        <strong>공식 페이지를 내부에 띄우지 않는 이유</strong>
        <span>제조사 사이트가 다른 도메인의 iframe 표시를 제한하므로, 기능이 깨지지 않는 공식 새 탭 연결 방식을 사용합니다.</span>
      </div>
    </section>
  );
}
