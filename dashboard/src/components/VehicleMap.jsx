/**
 * SmartV2X-CP Ultra — Live Vehicle Map
 * Leaflet map with auto-updating vehicle markers color-coded by risk.
 */
import React, { useEffect, useRef } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap, CircleMarker } from 'react-leaflet';
import L from 'leaflet';

// Fix default marker icons in bundled environments
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
    iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
    iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
});

const RISK_COLORS = {
    HIGH: '#ef4444',
    MEDIUM: '#f59e0b',
    LOW: '#10b981',
};

function VehicleMarkers({ vehicles }) {
    return (
        <>
            {Object.values(vehicles).map((v) => {
                const lat = v.last_telemetry?.latitude || 0;
                const lon = v.last_telemetry?.longitude || 0;
                if (!lat && !lon) return null;

                const riskProb = v.last_telemetry?.collision_probability || 0;
                const riskLevel = riskProb > 0.6 ? 'HIGH' : riskProb > 0.3 ? 'MEDIUM' : 'LOW';
                const color = RISK_COLORS[riskLevel] || RISK_COLORS.LOW;

                return (
                    <CircleMarker
                        key={v.id}
                        center={[lat, lon]}
                        radius={10}
                        pathOptions={{
                            fillColor: color,
                            fillOpacity: 0.8,
                            color: color,
                            weight: 2,
                            opacity: 1,
                        }}
                    >
                        <Popup>
                            <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 13 }}>
                                <strong>{v.name}</strong>
                                <br />
                                Speed: {v.last_telemetry?.speed || '0'} km/h
                                <br />
                                Risk: <span style={{ color, fontWeight: 600 }}>{riskLevel} ({Math.round(riskProb * 100)}%)</span>
                                <br />
                                Last sync: {v.last_telemetry ? new Date(v.last_telemetry.timestamp).toLocaleTimeString() : 'N/A'}
                            </div>
                        </Popup>
                    </CircleMarker>
                );
            })}
        </>
    );
}

export default function VehicleMap({ vehicles = {} }) {
    const defaultCenter = [28.6139, 77.209];
    const defaultZoom = 13;

    return (
        <div className="map-container">
            <MapContainer center={defaultCenter} zoom={defaultZoom} style={{ height: '100%', width: '100%' }}>
                <TileLayer
                    attribution='&copy; <a href="https://www.openstreetmap.org">OpenStreetMap</a>'
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />
                <VehicleMarkers vehicles={vehicles} />
            </MapContainer>
        </div>
    );
}
