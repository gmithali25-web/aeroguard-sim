// AeroGuard Sim - 3D Globe & Rocket Launch Simulation (Cesium.js Engine)
// Requires Cesium Viewer container in index.html

const viewer = new Cesium.Viewer('cesiumContainer', {
    terrainProvider: Cesium.createWorldTerrain(),
    animation: true,
    timeline: true,
    baseLayerPicker: true
});

// Configure camera view over Kennedy Space Center launch pad
viewer.camera.setView({
    destination: Cesium.Cartesian3.fromDegrees(-80.6041, 28.5729, 2500000),
    orientation: {
        heading: Cesium.Math.toRadians(0.0),
        pitch: Cesium.Math.toRadians(-45.0),
        roll: 0.0
    }
});

// Rocket Archetypes Catalog
const rocketModels = {
    "Saturn V": { thrust_kN: 35100, dry_mass_kg: 130000, profile: "Heavy-Lift Lunar Ascent" },
    "Falcon 9": { thrust_kN: 7607, dry_mass_kg: 22200, profile: "Orbital Insertion Gravity Turn" },
    "NASA SLS": { thrust_kN: 39130, dry_mass_kg: 98000, profile: "Deep Space Exploration Profile" }
};

// Function to trigger live gravity-turn launch animation with fire hazard visualizer
function launchRocket(rocketName, fuelMaterial, initialOxygen) {
    console.log(`Initiating launch sequence for ${rocketName} using ${fuelMaterial} fuel.`);
    
    // Create animated entity representing the ascending rocket trajectory
    const startTime = Cesium.JulianDate.now();
    const stopTime = Cesium.JulianDate.addSeconds(startTime, 120, new Cesium.JulianDate());

    viewer.clock.startTime = startTime.clone();
    viewer.clock.stopTime = stopTime.clone();
    viewer.clock.currentTime = startTime.clone();
    viewer.clock.clockRange = Cesium.ClockRange.LOOP_STOP;
    viewer.clock.multiplier = 2.0;

    const positionProperty = new Cesium.SampledPositionProperty();
    
    // Simulate parabolic gravity-turn trajectory coordinates from launch site
    let lon = -80.6041;
    let lat = 28.5729;
    let alt = 0;

    for (let i = 0; i <= 120; i += 5) {
        const time = Cesium.JulianDate.addSeconds(startTime, i, new Cesium.JulianDate());
        lon += 0.01 * (i / 10); // Gravity turn curve
        lat += 0.008 * (i / 10);
        alt += i * 1500; // Ascending altitude

        const position = Cesium.Cartesian3.fromDegrees(lon, lat, alt);
        positionProperty.addSample(time, position);
    }

    const entity = viewer.entities.add({
        availability: new Cesium.TimeIntervalCollection([new Cesium.TimeInterval({ start: startTime, stop: stopTime })]),
        position: positionProperty,
        point: {
            pixelSize: 14,
            color: Cesium.Color.ORANGERED // Simulates live thermal/fire hazard glow during Max-Q
        },
        path: {
            resolution: 1,
            material: new Cesium.PolylineGlowMaterialProperty({
                glowPower: 0.2,
                color: Cesium.Color.CYAN
            }),
            width: 5
        }
    });

    viewer.trackedEntity = entity;
}
