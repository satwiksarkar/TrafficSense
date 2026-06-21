import os
import json
import logging
from service.db.db_handler import TrafficReportManager, NewsReportManager
from service.route_recomend.route_management import RouteManager
from service.prediction_model.prediction_service import predict_traffic_impact
from service.db.util import load_city_traffic_stations

logger = logging.getLogger(__name__)

class TrafficAssignmentManager:
    def __init__(self, report_manager: TrafficReportManager, news_manager: NewsReportManager, route_manager: RouteManager):
        self.report_manager = report_manager
        self.news_manager = news_manager
        self.route_manager = route_manager

    def assign_reports(self, city_name="Bangalore"):
        """
        Fetches active reports, resolves closest station vectors, pulls driving polylines, 
        and extracts localized asset inventories for frontend display.
        """
        # 1. Gather live reported active alerts
        active_reports = self.report_manager.get_active_incidents()
        assignments = []

        if not active_reports:
            print("[Assignment Manager]: No active reports to evaluate today.")
            return []

        for report in active_reports:
            # Handle potential variation in dict mapping schemes (lat vs mean_lat)
            lat = report.get("mean_lat") or report.get("lat")
            lng = report.get("mean_lng") or report.get("lng") or report.get("long")
            
            if lat is None or lng is None:
                continue

            # 2. Extract spatial routing details & station proximity matches
            route_assignment = self.route_manager.assign_station_to_incident(
                incident_lat=float(lat), 
                incident_lon=float(lng), 
                city_name=city_name
            )

            if "error" in route_assignment:
                logger.warning(f"Failed to resolve route metrics for report {report.get('id')}")
                continue

            # 3. Pull predictive timeline models & asset requirements 
            # (Utilizing predict_traffic_impact without modification)
            dispatch_details = predict_traffic_impact(
                latitude=float(lat),
                longitude=float(lng),
                event_cause=report.get("issue_type", "CONGESTION"),
                priority=report.get("priority", "MEDIUM"),
                description=report.get("description", "Traffic incident reported")
            )

            # 4. Bind information arrays into a single unified frontend record payload
            assigned_station_name = route_assignment["assigned_station"]
            
            # Fetch local station inventory from the JSON profile
            all_stations = load_city_traffic_stations(self.report_manager.get_db_dir(),city_name)
            station_profile = next((s for s in all_stations if s["station_name"] == assigned_station_name), {})
            local_inventory = station_profile.get("inventory", {})

            unified_payload = {
                "report_id": report.get("id"),
                "issue_type": report.get("issue_type"),
                "location_name": report.get("location_name"),
                "coordinates": {"lat": float(lat), "lng": float(lng)},
                "assignment": {
                    "station_name": assigned_station_name,
                    "station_coordinates": route_assignment["station_location"],
                    "distance_km": route_assignment["distance_km"],
                    "route_polyline": route_assignment["route"]
                },
                "predictive_metrics": dispatch_details.get("traffic_prediction", {}),
                "detour_routing": dispatch_details.get("routing", {}),
                "scheduling": {
                    "allocated_resources": dispatch_details.get("resource_allocation", {}),
                    "station_local_inventory": local_inventory
                }
            }
            
            assignments.append(unified_payload)

        return assignments

# =====================================================================
# TEST BENCH & MOCK ARCHITECTURE FOR LOCAL SYSTEM VALIDATION
# =====================================================================

class MockTrafficReportManager:
    """Simulates active operational incident alerts."""
    def get_db_dir(self):
        # Assumes database/ directory sits relative to root execution space
        import os
        return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "database"))

    def get_active_incidents(self):
        return [
            {
                "id": "REP_101",
                "issue_type": "ACCIDENT",
                "location_name": "Near Silk Board Flyover",
                "lat": 12.9165,
                "lng": 77.6210,
                "priority": "CRITICAL",
                "description": "Major multi-car pileup blocking 2 lanes near Silk Board Junction. Needs urgent heavy tow support."
            },
            {
                "id": "REP_102",
                "issue_type": "CONGESTION",
                "location_name": "Hebbal Approach Road",
                "lat": 13.0320,
                "lng": 77.5995,
                "priority": "HIGH",
                "description": "Severe bottleneck forming on the flyover ramp due to stalled vehicle."
            }
        ]





class MockNewsReportManager:
    """Mock fallback for news interface arrays."""
    pass

class MockRouteManager:
    """Mocks spatial geometry matching operations."""
    def assign_station_to_incident(self, incident_lat, incident_lon, city_name):
        # Rough vector logic to assign realistic target station strings for test outputs
        if incident_lat < 12.95:
            assigned = "Silk Board Junction"
            station_loc = {"lat": 12.9177, "lon": 77.6229}
        else:
            assigned = "Hebbal Flyover Junction"
            station_loc = {"lat": 13.0355, "lon": 77.5970}
            
        return {
            "assigned_station": assigned,
            "station_location": station_loc,
            "distance_km": 0.42,
            "route": [[station_loc["lat"], station_loc["lon"]], [incident_lat, incident_lon]]
        }

if __name__ == "__main__":
    import pprint
    print("\n🔍 [Testing initialization]: Setting up Mock Infrastructure Layers...")
    
    # 1. Instantiate the mock system variations
    mock_report = MockTrafficReportManager()
    mock_news = MockNewsReportManager()
    mock_route = MockRouteManager()
    
    # 2. Wire the mock wrappers into your production TrafficAssignmentManager
    print("🚀 [Instantiation]: Initializing TrafficAssignmentManager...")
    manager = TrafficAssignmentManager(
        report_manager=mock_report, # type: ignore
        news_manager=mock_news,     # type: ignore
        route_manager=mock_route    # type: ignore
    )
    
    # 3. Dynamically evaluate the tracking assignments across data loops
    print("📊 [Processing]: Running Report Allocation Algorithm for 'Bangalore'...")
    try:
        results = manager.assign_reports(city_name="Bangalore")
        
        print("\n========================= ASSIGNMENT OUTPUT RESULTS =========================\n")
        pprint.pprint(results, indent=2, width=100)
        print("\n=============================================================================\n")
        print(f"✅ Success: Processed and matched {len(results)} layout schedules cleanly.")
        
    except Exception as e:
        print(f"❌ Critical Failure during Execution: {e}")
        import traceback
        traceback.print_exc()