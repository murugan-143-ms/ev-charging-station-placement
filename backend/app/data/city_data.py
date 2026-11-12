import math
from typing import List, Dict, Any
from app.models.schemas import CityBoundary, DemandPoint, PowerGridNode

# ==========================================
# Scenario 1: Austin Metro EV Corridor (Texas)
# Center: [30.2747, -97.7404]
# ==========================================

AUSTIN_BOUNDARY_COORDS: List[List[float]] = [
    [30.4350, -97.7400],  # North / Tech Ridge
    [30.4050, -97.6600],  # Northeast / Parmer
    [30.3400, -97.6300],  # East / Walter E. Long
    [30.2600, -97.6200],  # East SH-130 / Gigafactory Area
    [30.1900, -97.6500],  # Southeast / Airport East
    [30.1500, -97.7200],  # South East / McKinney Falls
    [30.1450, -97.8000],  # Far South / Onion Creek
    [30.1700, -97.8700],  # Southwest / Slaughter & Mopac
    [30.2200, -97.8900],  # Oak Hill / Southwest Parkway
    [30.2800, -97.8500],  # Westlake Hills / Barton Creek
    [30.3400, -97.8200],  # Northwest / 2222 Bull Creek
    [30.4100, -97.8000],  # Arboretum / Great Hills
    [30.4400, -97.7600],  # North / Wells Branch
    [30.4350, -97.7400],  # Closed
]

AUSTIN_GRID_NODES: List[PowerGridNode] = [
    PowerGridNode(id="grid-1", name="Downtown Metro Substation 138kV", lat=30.2680, lng=-97.7450, voltage_kv=138),
    PowerGridNode(id="grid-2", name="Domain Tech Energy Hub 138kV", lat=30.4020, lng=-97.7260, voltage_kv=138),
    PowerGridNode(id="grid-3", name="Bergstrom Airport Feeder 69kV", lat=30.2010, lng=-97.6720, voltage_kv=69),
    PowerGridNode(id="grid-4", name="East Austin Industrial Station 138kV", lat=30.2580, lng=-97.6650, voltage_kv=138),
    PowerGridNode(id="grid-5", name="Oak Hill South Substation 69kV", lat=30.2250, lng=-97.8550, voltage_kv=69),
    PowerGridNode(id="grid-6", name="Northwest Tech Corridor Substation 138kV", lat=30.3800, lng=-97.7800, voltage_kv=138),
    PowerGridNode(id="grid-7", name="South Congress Distribution Node 69kV", lat=30.2100, lng=-97.7700, voltage_kv=69),
]

AUSTIN_DEMAND_POINTS: List[DemandPoint] = [
    # Downtown & Core Commercial
    DemandPoint(id="dp-01", name="Austin Downtown Center", lat=30.2672, lng=-97.7431, weight=96, category="Commercial Hub", expected_ev_count=210),
    DemandPoint(id="dp-02", name="Texas State Capitol District", lat=30.2747, lng=-97.7404, weight=88, category="Commercial Hub", expected_ev_count=180),
    DemandPoint(id="dp-03", name="UT Austin Main Campus", lat=30.2849, lng=-97.7341, weight=92, category="Tech Park", expected_ev_count=240),
    DemandPoint(id="dp-04", name="Rainey Street Historic District", lat=30.2590, lng=-97.7380, weight=75, category="Retail Mall", expected_ev_count=130),
    DemandPoint(id="dp-05", name="South Congress (SoCo) Ave", lat=30.2500, lng=-97.7490, weight=82, category="Retail Mall", expected_ev_count=160),
    DemandPoint(id="dp-06", name="Lady Bird Lake Trailhead & Parks", lat=30.2605, lng=-97.7600, weight=65, category="Transit Station", expected_ev_count=110),
    DemandPoint(id="dp-07", name="Zilker Park & Barton Springs", lat=30.2640, lng=-97.7710, weight=78, category="Retail Mall", expected_ev_count=145),

    # North Tech Hub (The Domain & Arboretum)
    DemandPoint(id="dp-08", name="The Domain Central Tech Plaza", lat=30.4021, lng=-97.7258, weight=95, category="Tech Park", expected_ev_count=260),
    DemandPoint(id="dp-09", name="Domain Northside Retail", lat=30.4070, lng=-97.7220, weight=86, category="Retail Mall", expected_ev_count=190),
    DemandPoint(id="dp-10", name="IBM Innovation Center Austin", lat=30.3950, lng=-97.7180, weight=80, category="Tech Park", expected_ev_count=170),
    DemandPoint(id="dp-11", name="Arboretum at Great Hills", lat=30.3920, lng=-97.7480, weight=74, category="Retail Mall", expected_ev_count=140),
    DemandPoint(id="dp-12", name="Apple Americas Operations Campus", lat=30.4280, lng=-97.7550, weight=94, category="Tech Park", expected_ev_count=250),
    DemandPoint(id="dp-13", name="Tech Ridge Center Park & Ride", lat=30.4080, lng=-97.6740, weight=72, category="Transit Station", expected_ev_count=130),
    DemandPoint(id="dp-14", name="Wells Branch Crossing", lat=30.4350, lng=-97.6850, weight=62, category="Residential", expected_ev_count=95),

    # Airport & Southeast Corridor
    DemandPoint(id="dp-15", name="Austin-Bergstrom Airport Terminal (ABIA)", lat=30.1975, lng=-97.6664, weight=98, category="Airport/Logistics", expected_ev_count=320),
    DemandPoint(id="dp-16", name="ABIA Rental Car & Logistics Center", lat=30.2030, lng=-97.6690, weight=84, category="Airport/Logistics", expected_ev_count=195),
    DemandPoint(id="dp-17", name="Tesla Giga Texas Logistics Zone", lat=30.2220, lng=-97.6180, weight=93, category="Tech Park", expected_ev_count=280),
    DemandPoint(id="dp-18", name="Del Valle Regional Transit Hub", lat=30.1980, lng=-97.6350, weight=55, category="Transit Station", expected_ev_count=85),
    DemandPoint(id="dp-19", name="McKinney Falls Community Hub", lat=30.1780, lng=-97.7220, weight=48, category="Residential", expected_ev_count=70),

    # East Austin Cultural & Tech Corridor
    DemandPoint(id="dp-20", name="East 6th Street Tech Offices", lat=30.2640, lng=-97.7220, weight=81, category="Tech Park", expected_ev_count=155),
    DemandPoint(id="dp-21", name="East Cesar Chavez Commercial Hub", lat=30.2540, lng=-97.7180, weight=70, category="Commercial Hub", expected_ev_count=120),
    DemandPoint(id="dp-22", name="Mueller Town Center Plaza", lat=30.3010, lng=-97.7080, weight=89, category="Commercial Hub", expected_ev_count=190),
    DemandPoint(id="dp-23", name="Dell Children's Medical Center", lat=30.3050, lng=-97.7050, weight=76, category="Commercial Hub", expected_ev_count=140),
    DemandPoint(id="dp-24", name="Springdale General Tech Arts", lat=30.2880, lng=-97.6950, weight=67, category="Tech Park", expected_ev_count=115),
    DemandPoint(id="dp-25", name="Govalle Regional Logistics", lat=30.2620, lng=-97.6980, weight=58, category="Airport/Logistics", expected_ev_count=90),

    # South Austin Commercial & Residential
    DemandPoint(id="dp-26", name="Barton Creek Square Mall", lat=30.2570, lng=-97.8080, weight=87, category="Retail Mall", expected_ev_count=185),
    DemandPoint(id="dp-27", name="South Lamar Commercial Corridor", lat=30.2450, lng=-97.7780, weight=79, category="Commercial Hub", expected_ev_count=150),
    DemandPoint(id="dp-28", name="Westgate Shopping Center", lat=30.2280, lng=-97.8030, weight=71, category="Retail Mall", expected_ev_count=125),
    DemandPoint(id="dp-29", name="St. Edward's University Campus", lat=30.2300, lng=-97.7540, weight=73, category="Tech Park", expected_ev_count=130),
    DemandPoint(id="dp-30", name="Southpark Meadows Regional Center", lat=30.1650, lng=-97.7880, weight=85, category="Retail Mall", expected_ev_count=175),
    DemandPoint(id="dp-31", name="Slaughter Lane & Menchaca Hub", lat=30.1800, lng=-97.8280, weight=68, category="Residential", expected_ev_count=110),
    DemandPoint(id="dp-32", name="Circle C Ranch Community Center", lat=30.1980, lng=-97.8720, weight=74, category="Residential", expected_ev_count=135),
    DemandPoint(id="dp-33", name="Oak Hill Crossroads Plaza", lat=30.2350, lng=-97.8630, weight=66, category="Transit Station", expected_ev_count=105),

    # Northwest & Central Residential/Commercial
    DemandPoint(id="dp-34", name="North MoPac Office Park", lat=30.3480, lng=-97.7480, weight=77, category="Commercial Hub", expected_ev_count=145),
    DemandPoint(id="dp-35", name="Burnet Road Food & Retail Corridor", lat=30.3420, lng=-97.7320, weight=73, category="Retail Mall", expected_ev_count=130),
    DemandPoint(id="dp-36", name="Highland ACC Campus & Rail Station", lat=30.3270, lng=-97.7160, weight=83, category="Transit Station", expected_ev_count=160),
    DemandPoint(id="dp-37", name="Hyde Park Historic Neighborhood", lat=30.3060, lng=-97.7300, weight=59, category="Residential", expected_ev_count=85),
    DemandPoint(id="dp-38", name="Brentwood Community Village", lat=30.3340, lng=-97.7250, weight=56, category="Residential", expected_ev_count=80),
    DemandPoint(id="dp-39", name="Crestview MetroRail Station", lat=30.3440, lng=-97.7170, weight=78, category="Transit Station", expected_ev_count=135),
    DemandPoint(id="dp-40", name="Far West Blvd Residential Hub", lat=30.3550, lng=-97.7580, weight=63, category="Residential", expected_ev_count=95),
    DemandPoint(id="dp-41", name="Bull Creek Gateway Park", lat=30.3700, lng=-97.7850, weight=52, category="Residential", expected_ev_count=70),
    DemandPoint(id="dp-42", name="Anderson Mill North Gateway", lat=30.4180, lng=-97.7800, weight=68, category="Residential", expected_ev_count=110),

    # Peripheral & Specialized Demand Zones
    DemandPoint(id="dp-43", name="Braker Lane Commercial Complex", lat=30.3860, lng=-97.7020, weight=71, category="Commercial Hub", expected_ev_count=120),
    DemandPoint(id="dp-44", name="Metric Blvd Tech Corridors", lat=30.3980, lng=-97.7080, weight=75, category="Tech Park", expected_ev_count=130),
    DemandPoint(id="dp-45", name="Riverside Drive Student Living", lat=30.2420, lng=-97.7240, weight=69, category="Residential", expected_ev_count=115),
    DemandPoint(id="dp-46", name="Montopolis Community Center", lat=30.2310, lng=-97.7010, weight=54, category="Residential", expected_ev_count=75),
    DemandPoint(id="dp-47", name="Onion Creek Golf & Subdivisions", lat=30.1550, lng=-97.7720, weight=61, category="Residential", expected_ev_count=90),
    DemandPoint(id="dp-48", name="Brodie Lane Shopping Strip", lat=30.2150, lng=-97.8280, weight=70, category="Retail Mall", expected_ev_count=120),
    DemandPoint(id="dp-49", name="Westlake Hills Village Center", lat=30.2920, lng=-97.8050, weight=82, category="Residential", expected_ev_count=165),
    DemandPoint(id="dp-50", name="Walnut Creek Corporate Park", lat=30.3750, lng=-97.6720, weight=65, category="Airport/Logistics", expected_ev_count=100),
]


# ==========================================
# Scenario 2: San Francisco Bay Peninsula
# Center: [37.7600, -122.4400]
# ==========================================

SF_BOUNDARY_COORDS: List[List[float]] = [
    [37.8100, -122.4750],  # Presidio North
    [37.8100, -122.4150],  # Fisherman's Wharf
    [37.7950, -122.3900],  # Embarcadero
    [37.7750, -122.3850],  # Mission Bay
    [37.7400, -122.3800],  # Hunters Point
    [37.7100, -122.4000],  # Visitacion Valley
    [37.6950, -122.4600],  # Daly City Border
    [37.7200, -122.5050],  # Lake Merced
    [37.7600, -122.5100],  # Ocean Beach
    [37.7900, -122.5000],  # Lands End
    [37.8100, -122.4750],  # Closed
]

SF_GRID_NODES: List[PowerGridNode] = [
    PowerGridNode(id="sf-grid-1", name="Downtown Transbay Substation 230kV", lat=37.7900, lng=-122.4000, voltage_kv=230),
    PowerGridNode(id="sf-grid-2", name="Mission Bay Medical Grid Node", lat=37.7680, lng=-122.3920, voltage_kv=115),
    PowerGridNode(id="sf-grid-3", name="Twin Peaks South Central Grid Node", lat=37.7500, lng=-122.4450, voltage_kv=115),
    PowerGridNode(id="sf-grid-4", name="Ocean Beach Westside Feeder", lat=37.7550, lng=-122.4950, voltage_kv=69),
    PowerGridNode(id="sf-grid-5", name="Bayshore South Substation 115kV", lat=37.7150, lng=-122.4100, voltage_kv=115),
]

SF_DEMAND_POINTS: List[DemandPoint] = [
    DemandPoint(id="sfd-01", name="Financial District & SalesForce Tower", lat=37.7905, lng=-122.4000, weight=98, category="Commercial Hub", expected_ev_count=290),
    DemandPoint(id="sfd-02", name="Union Square Retail Center", lat=37.7879, lng=-122.4074, weight=90, category="Retail Mall", expected_ev_count=210),
    DemandPoint(id="sfd-03", name="SoMa Tech Cluster", lat=37.7800, lng=-122.4050, weight=94, category="Tech Park", expected_ev_count=260),
    DemandPoint(id="sfd-04", name="Mission Bay UCSF Medical Center", lat=37.7670, lng=-122.3920, weight=92, category="Tech Park", expected_ev_count=230),
    DemandPoint(id="sfd-05", name="Oracle Park & South Beach", lat=37.7780, lng=-122.3890, weight=84, category="Retail Mall", expected_ev_count=180),
    DemandPoint(id="sfd-06", name="Mission District 16th BART", lat=37.7650, lng=-122.4200, weight=86, category="Transit Station", expected_ev_count=190),
    DemandPoint(id="sfd-07", name="The Castro Cultural District", lat=37.7610, lng=-122.4350, weight=78, category="Commercial Hub", expected_ev_count=145),
    DemandPoint(id="sfd-08", name="Twin Peaks Scenic Overlook", lat=37.7540, lng=-122.4460, weight=62, category="Retail Mall", expected_ev_count=90),
    DemandPoint(id="sfd-09", name="Noe Valley Neighborhood Strip", lat=37.7500, lng=-122.4330, weight=74, category="Residential", expected_ev_count=130),
    DemandPoint(id="sfd-10", name="Bernal Heights Community", lat=37.7420, lng=-122.4180, weight=66, category="Residential", expected_ev_count=110),
    DemandPoint(id="sfd-11", name="Dogpatch Arts & Maker District", lat=37.7580, lng=-122.3880, weight=72, category="Commercial Hub", expected_ev_count=120),
    DemandPoint(id="sfd-12", name="Potrero Hill High-Tech Lofts", lat=37.7550, lng=-122.4000, weight=75, category="Residential", expected_ev_count=135),
    DemandPoint(id="sfd-13", name="Fisherman's Wharf & Pier 39", lat=37.8080, lng=-122.4120, weight=88, category="Retail Mall", expected_ev_count=195),
    DemandPoint(id="sfd-14", name="Marina District Chestnut Street", lat=37.8010, lng=-122.4380, weight=81, category="Commercial Hub", expected_ev_count=160),
    DemandPoint(id="sfd-15", name="Pacific Heights Residential", lat=37.7920, lng=-122.4350, weight=85, category="Residential", expected_ev_count=175),
    DemandPoint(id="sfd-16", name="Inner Richmond Geary Boulevard", lat=37.7810, lng=-122.4650, weight=76, category="Commercial Hub", expected_ev_count=135),
    DemandPoint(id="sfd-17", name="Outer Sunset Judah Corridor", lat=37.7620, lng=-122.4920, weight=68, category="Residential", expected_ev_count=115),
    DemandPoint(id="sfd-18", name="Stonestown Galleria & SFSU", lat=37.7270, lng=-122.4760, weight=87, category="Retail Mall", expected_ev_count=200),
    DemandPoint(id="sfd-19", name="Glen Park BART Station", lat=37.7330, lng=-122.4340, weight=77, category="Transit Station", expected_ev_count=140),
    DemandPoint(id="sfd-20", name="Balboa Park Multi-Modal Transit", lat=37.7220, lng=-122.4470, weight=80, category="Transit Station", expected_ev_count=155),
    DemandPoint(id="sfd-21", name="Hunters Point Shipyard Re-dev", lat=37.7320, lng=-122.3780, weight=60, category="Tech Park", expected_ev_count=95),
    DemandPoint(id="sfd-22", name="Bayshore Caltrain Terminal", lat=37.7080, lng=-122.4020, weight=73, category="Transit Station", expected_ev_count=125),
    DemandPoint(id="sfd-23", name="Ocean Beach Pavilion", lat=37.7650, lng=-122.5080, weight=65, category="Retail Mall", expected_ev_count=100),
    DemandPoint(id="sfd-24", name="Golden Gate Park Music Concourse", lat=37.7710, lng=-122.4670, weight=79, category="Transit Station", expected_ev_count=145),
    DemandPoint(id="sfd-25", name="Presidio Officers' Club Tech Park", lat=37.7980, lng=-122.4600, weight=70, category="Tech Park", expected_ev_count=120),
]


def get_scenario_data(scenario_id: str = "austin_metro") -> Dict[str, Any]:
    if scenario_id == "san_francisco_bay":
        min_lat = min(pt[0] for pt in SF_BOUNDARY_COORDS)
        max_lat = max(pt[0] for pt in SF_BOUNDARY_COORDS)
        min_lng = min(pt[1] for pt in SF_BOUNDARY_COORDS)
        max_lng = max(pt[1] for pt in SF_BOUNDARY_COORDS)
        return {
            "city_boundary": CityBoundary(
                name="San Francisco Peninsula EV Grid",
                polygon=SF_BOUNDARY_COORDS,
                center=[37.7600, -122.4400],
                bounding_box={"min_lat": min_lat, "max_lat": max_lat, "min_lng": min_lng, "max_lng": max_lng}
            ),
            "power_grid_nodes": SF_GRID_NODES,
            "demand_points": SF_DEMAND_POINTS,
        }
    else:  # Default Austin Metro
        min_lat = min(pt[0] for pt in AUSTIN_BOUNDARY_COORDS)
        max_lat = max(pt[0] for pt in AUSTIN_BOUNDARY_COORDS)
        min_lng = min(pt[1] for pt in AUSTIN_BOUNDARY_COORDS)
        max_lng = max(pt[1] for pt in AUSTIN_BOUNDARY_COORDS)
        return {
            "city_boundary": CityBoundary(
                name="Austin Metropolitan Area (Texas EV Corridor)",
                polygon=AUSTIN_BOUNDARY_COORDS,
                center=[30.2747, -97.7404],
                bounding_box={"min_lat": min_lat, "max_lat": max_lat, "min_lng": min_lng, "max_lng": max_lng}
            ),
            "power_grid_nodes": AUSTIN_GRID_NODES,
            "demand_points": AUSTIN_DEMAND_POINTS,
        }

