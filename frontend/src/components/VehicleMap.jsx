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
    LOW: '#22d3ee',
    MEDIUM: '#fcd34d',
    HIGH: '#f87171'
};

const VEHICLE_ICON_SVG = `
<svg width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M6 18V24C6 25.1046 6.89543 26 8 26H9M26 18V24C26 25.1046 25.1046 26 24 26H23" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
    <path d="M4 14C4 12.8954 4.89543 12 6 12H26C27.1046 12 28 12.8954 28 14V19C28 20.1046 27.1046 21 26 21H6C4.89543 21 4 20.1046 4 19V14Z" fill="currentColor"/>
    <rect x="7" y="14" width="18" height="4" rx="1" fill="white" fill-opacity="0.3"/>
    <circle cx="9" cy="24" r="3" stroke="currentColor" stroke-width="2"/>
    <circle cx="23" cy="24" r="3" stroke="currentColor" stroke-width="2"/>
</svg>
`;

function VehicleMarkers({ vehicles }) {
    return (
        <>
            {Object.values(vehicles).map((v) => {
                const lat = v.latitude || 0;
                const lon = v.longitude || 0;
                if (!lat && !lon) return null;

                const riskProb = v.collision_probability || 0;
                const riskLevel = riskProb > 0.6 ? 'HIGH' : riskProb > 0.3 ? 'MEDIUM' : 'LOW';
                const color = RISK_COLORS[riskLevel] || RISK_COLORS.LOW;

                const icon = L.divIcon({
                    className: 'custom-vehicle-icon',
                    html: `<div style="color: ${color}; transform: rotate(${v.heading || 0}deg); transition: all 1s linear;">${VEHICLE_ICON_SVG}</div>`,
                    iconSize: [32, 32],
                    iconAnchor: [16, 16],
                });

                return (
                    <Marker
                        key={v.id}
                        position={[lat, lon]}
                        icon={icon}
                    >
                        <Popup>
                            <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 13 }}>
                                <strong>{v.name}</strong>
                                <br />
                                Speed: {v.speed || '0'} km/h
                                <br />
                                Risk: <span style={{ color, fontWeight: 600 }}>{riskLevel} ({Math.round(riskProb * 100)}%)</span>
                            </div>
                        </Popup>
                    </Marker>
                );
            })}
        </>
    );
}

export default function VehicleMap({ vehicles = [] }) {
    const defaultCenter = [37.7749, -122.4194]; // Updated to match pi_sender mock coordinates
    const defaultZoom = 15;

    return (
        <div className="map-container">
            <style>
                {`
                .leaflet-marker-icon {
                    transition: all 1s linear;
                }
                `}
            </style>
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
