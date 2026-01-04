import React, { useEffect, useMemo, useRef } from "react";
import useNaverMapLoader from "../lib/useNaverMapLoader";

const defaultCenter = { lat: 37.5665, lng: 126.9780 }; // 서울 시청

/**
 * props:
 * - markers: [{ id, lat, lng, title, html? }]
 * - height: number | string (px)
 * - fitToMarkers: boolean
 * - onMarkerClick: (markerData) => void
 */
export default function NaverMap({
  markers = [],
  height = 560,
  fitToMarkers = true,
  onMarkerClick,
}) {
  const { loaded, error } = useNaverMapLoader({ submodules: ["geocoder"] });
  const boxRef = useRef(null);
  const mapRef = useRef(null);
  const infoWindow = useMemo(
    () => (loaded ? new window.naver.maps.InfoWindow({ anchorSkew: true }) : null),
    [loaded]
  );

  // 지도 생성
  useEffect(() => {
    if (!loaded || error || !boxRef.current) return;
    if (!mapRef.current) {
      mapRef.current = new window.naver.maps.Map(boxRef.current, {
        center: new window.naver.maps.LatLng(defaultCenter.lat, defaultCenter.lng),
        zoom: 12,
        minZoom: 7,
        zoomControl: true,
        zoomControlOptions: { position: window.naver.maps.Position.TOP_RIGHT },
      });
    }
  }, [loaded, error]);

  // 마커 렌더링
  useEffect(() => {
    if (!loaded || !mapRef.current) return;

    // 기존 마커 제거
    if (!mapRef.current.__markers) mapRef.current.__markers = [];
    mapRef.current.__markers.forEach((m) => m.setMap(null));
    mapRef.current.__markers = [];

    markers.forEach((m) => {
      const marker = new window.naver.maps.Marker({
        position: new window.naver.maps.LatLng(m.lat, m.lng),
        map: mapRef.current,
        title: m.title || "",
      });
      window.naver.maps.Event.addListener(marker, "click", () => {
        if (infoWindow) {
          infoWindow.setContent(
            m.html ||
              `<div style="padding:8px 10px">
                 <b>${m.title ?? "상세보기"}</b><br/>
                 <small>${m.lat.toFixed(5)}, ${m.lng.toFixed(5)}</small>
               </div>`
          );
          infoWindow.open(mapRef.current, marker);
        }
        onMarkerClick && onMarkerClick(m);
      });
      mapRef.current.__markers.push(marker);
    });

    if (fitToMarkers && mapRef.current.__markers.length > 0) {
      const bounds = new window.naver.maps.LatLngBounds();
      mapRef.current.__markers.forEach((mk) => bounds.extend(mk.getPosition()));
      mapRef.current.fitBounds(bounds);
    }
  }, [markers, loaded, fitToMarkers, onMarkerClick, infoWindow]);

  if (error) return <div style={{ color: "red" }}>지도 로드 오류: {error}</div>;
  return <div ref={boxRef} style={{ width: "100%", height }} />;
}