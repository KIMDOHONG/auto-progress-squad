# ADR-0009: 선택형 서버 측 NAVER Maps 경로 공급자

- 날짜: 2026-09-01
- 상태: 승인
- 참여자: 자동차진행단 프로젝트 팀

## 배경

Issue #5의 로컬 주행 플래너는 경로 거리를 직접 입력해 EV 에너지와 수소·내연기관 주행가능거리를 계산한다. 실제 출발지와 목적지에서 거리·예상 시간을 얻으려면 주소 좌표 변환과 길찾기 API가 필요하지만, API 키가 없거나 상류 서비스가 실패해도 로컬 계산은 계속 사용할 수 있어야 한다.

## 검토한 선택지

1. 브라우저에서 NAVER Maps를 직접 호출한다.
2. FastAPI가 Geocoding과 Directions 5를 호출한다.
3. 외부 경로 API 없이 수동 거리 입력만 유지한다.

## 결정

- FastAPI에 `RouteProvider` 계약과 NAVER Maps 구현을 둔다.
- 주소는 공식 Geocoding API로 좌표화하고, 일반 승용차의 Directions 5 `trafast` 결과에서 거리와 예상 시간을 읽는다.
- 인증 Client ID와 Client Secret은 서버 환경변수에만 둔다. 브라우저에는 인증값을 전달하지 않는다.
- 공급자 미설정, 주소 불일치, 상류 장애를 서로 다른 오류로 반환한다.
- 프런트엔드는 실제 경로 조회를 사용자가 선택한 경우에만 호출한다. 성공하면 조회 거리를 로컬 계산에 넣고, 실패하면 오류를 표시하되 직접 입력 거리 계산을 그대로 제공한다.

공식 요청 계약은 [Geocoding](https://api.ncloud-docs.com/docs/application-maps-geocoding), [Directions 5](https://api.ncloud-docs.com/docs/application-maps-directions5), [Maps 공통 인증](https://api.ncloud-docs.com/docs/application-maps-overview)을 기준으로 한다.

## 근거

- Client Secret을 정적 웹앱에 노출하지 않는다.
- 외부 API 실패와 0 km 경로를 같은 상태로 오인하지 않는다.
- 기존 수동 입력 계산을 보존해 키·네트워크·한도에 의존하지 않는다.
- 공급자 계약을 분리해 다른 지도 공급자로 교체하거나 테스트 대역을 주입할 수 있다.

## 결과와 위험

- NAVER Maps 애플리케이션에서 Geocoding과 Directions 5를 모두 활성화해야 한다.
- 실제 경로는 실시간 교통 상황에 따라 같은 입력에서도 달라질 수 있다.
- 실제 계정 키를 사용한 라이브 E2E, 계정별 무료 한도와 과금 확인은 별도 운영 검증으로 남는다.
- 이 결정은 충전소·수소충전소·주유소 위치나 실시간 상태를 제공하지 않는다. 해당 데이터는 별도 공급자에서 연결한다.
