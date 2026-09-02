import { useEffect, useRef, useState } from "react";
import type { RouteAlternativeResult, RouteOption } from "../../lib/routeApi";

interface NaverOverlay {
  setMap(map: NaverMapInstance | null): void;
}

interface NaverMapInstance {
  fitBounds(bounds: NaverBoundsInstance, margin?: number): void;
  destroy(): void;
}

interface NaverBoundsInstance {
  extend(point: NaverLatLngInstance): void;
}

interface NaverLatLngInstance {}

interface NaverMapsNamespace {
  Map: new (element: HTMLElement, options: Record<string, unknown>) => NaverMapInstance;
  LatLng: new (latitude: number, longitude: number) => NaverLatLngInstance;
  LatLngBounds: new () => NaverBoundsInstance;
  Polyline: new (options: Record<string, unknown>) => NaverOverlay;
  Marker: new (options: Record<string, unknown>) => NaverOverlay;
}

declare global {
  interface Window {
    naver?: { maps: NaverMapsNamespace };
    __apsNaverMapPromise?: Promise<NaverMapsNamespace>;
  }
}

interface RouteMapProps {
  routes: RouteAlternativeResult[];
  selectedOption: RouteOption;
  browserClientId: string | null;
}

const ROUTE_COLORS: Record<RouteOption, string> = {
  trafast: "#2463eb",
  traoptimal: "#11a873",
  traavoidtoll: "#ef8a17",
};

function loadNaverMaps(browserClientId: string): Promise<NaverMapsNamespace> {
  if (window.naver?.maps) return Promise.resolve(window.naver.maps);
  if (window.__apsNaverMapPromise) return window.__apsNaverMapPromise;

  const mapPromise = new Promise<NaverMapsNamespace>((resolve, reject) => {
    const script = document.createElement("script");
    script.src = `https://oapi.map.naver.com/openapi/v3/maps.js?ncpKeyId=${encodeURIComponent(browserClientId)}`;
    script.async = true;
    script.addEventListener("load", () => {
      if (window.naver?.maps) resolve(window.naver.maps);
      else reject(new Error("NAVER 지도 SDK를 초기화하지 못했습니다."));
    }, { once: true });
    script.addEventListener("error", () => reject(new Error("NAVER 지도 SDK를 불러오지 못했습니다.")), { once: true });
    document.head.append(script);
  }).catch((error: unknown) => {
    window.__apsNaverMapPromise = undefined;
    throw error;
  });
  window.__apsNaverMapPromise = mapPromise;
  return mapPromise;
}

function RoutePathPreview({ routes, selectedOption }: Pick<RouteMapProps, "routes" | "selectedOption">) {
  const points = routes.flatMap((route) => route.path);
  if (points.length < 2) return null;
  const minLongitude = Math.min(...points.map((point) => point.longitude));
  const maxLongitude = Math.max(...points.map((point) => point.longitude));
  const minLatitude = Math.min(...points.map((point) => point.latitude));
  const maxLatitude = Math.max(...points.map((point) => point.latitude));
  const longitudeSpan = Math.max(maxLongitude - minLongitude, 0.00001);
  const latitudeSpan = Math.max(maxLatitude - minLatitude, 0.00001);
  const toSvgPoints = (route: RouteAlternativeResult) => route.path.map((point) => {
    const x = 24 + ((point.longitude - minLongitude) / longitudeSpan) * 552;
    const y = 24 + ((maxLatitude - point.latitude) / latitudeSpan) * 252;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");

  return (
    <svg className="route-path-preview" viewBox="0 0 600 300" role="img" aria-label="실제 경로 좌표 미리보기">
      {routes.map((route) => (
        <polyline
          key={route.routeOption}
          points={toSvgPoints(route)}
          fill="none"
          stroke={route.routeOption === selectedOption ? ROUTE_COLORS[route.routeOption] : "#aab5c6"}
          strokeWidth={route.routeOption === selectedOption ? 7 : 4}
          strokeLinecap="round"
          strokeLinejoin="round"
          opacity={route.routeOption === selectedOption ? 1 : 0.7}
        />
      ))}
    </svg>
  );
}

export function RouteMap({ routes, selectedOption, browserClientId }: RouteMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [mapError, setMapError] = useState("");

  useEffect(() => {
    if (!browserClientId || !containerRef.current || routes.length === 0) return undefined;
    let cancelled = false;
    let map: NaverMapInstance | null = null;
    let overlays: NaverOverlay[] = [];

    void loadNaverMaps(browserClientId).then((maps) => {
      if (cancelled || !containerRef.current) return;
      const selected = routes.find((route) => route.routeOption === selectedOption) ?? routes[0];
      const firstPoint = selected.path[0];
      if (!firstPoint) return;
      map = new maps.Map(containerRef.current, {
        center: new maps.LatLng(firstPoint.latitude, firstPoint.longitude),
        zoom: 11,
        scaleControl: true,
        mapDataControl: false,
      });
      const bounds = new maps.LatLngBounds();
      routes.forEach((route) => {
        const path = route.path.map((point) => {
          const latLng = new maps.LatLng(point.latitude, point.longitude);
          if (route.routeOption === selectedOption) bounds.extend(latLng);
          return latLng;
        });
        const overlay = new maps.Polyline({
          map,
          path,
          strokeColor: route.routeOption === selectedOption ? ROUTE_COLORS[route.routeOption] : "#9ba8ba",
          strokeOpacity: route.routeOption === selectedOption ? 0.95 : 0.55,
          strokeWeight: route.routeOption === selectedOption ? 7 : 4,
        });
        overlays.push(overlay);
      });
      const lastPoint = selected.path[selected.path.length - 1];
      overlays.push(new maps.Marker({ map, position: new maps.LatLng(firstPoint.latitude, firstPoint.longitude), title: "출발지" }));
      overlays.push(new maps.Marker({ map, position: new maps.LatLng(lastPoint.latitude, lastPoint.longitude), title: "목적지" }));
      map.fitBounds(bounds, 42);
      setMapError("");
    }).catch((error: unknown) => {
      if (!cancelled) setMapError(error instanceof Error ? error.message : "지도를 표시하지 못했습니다.");
    });

    return () => {
      cancelled = true;
      overlays.forEach((overlay) => overlay.setMap(null));
      overlays = [];
      map?.destroy();
    };
  }, [browserClientId, routes, selectedOption]);

  if (!browserClientId || mapError) {
    return (
      <div className="route-map-fallback">
        <RoutePathPreview routes={routes} selectedOption={selectedOption} />
        <span>{mapError || "Web Dynamic Map 키가 없어 실제 좌표 경로만 표시합니다."}</span>
      </div>
    );
  }

  return <div ref={containerRef} className="route-map" aria-label="NAVER 실제 도로 경로 지도" />;
}
