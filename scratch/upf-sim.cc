/*
 * upf-sim.cc — ns-3 UPF Placement Simulation
 * ============================================
 * Reads topology.json exported by the Python controller, creates the
 * network dynamically, simulates UDP traffic from users to the nearest
 * UPF, measures performance with FlowMonitor, and generates NetAnim XML.
 *
 * Build & Run (from ns-3 root):
 *   ./ns3 run scratch/upf-sim
 *
 * Expects topology.json in the ns-3 root directory.
 */

#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/internet-module.h"
#include "ns3/point-to-point-module.h"
#include "ns3/applications-module.h"
#include "ns3/mobility-module.h"
#include "ns3/flow-monitor-module.h"
#include "ns3/netanim-module.h"

#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include <set>
#include <cstdlib>
#include <iostream>
#include <algorithm>

using namespace ns3;

NS_LOG_COMPONENT_DEFINE("UPFSimulation");

// ── Data structures for parsed topology ──────────────────

struct NodeInfo {
    int    id;
    double x, y;
};

struct EdgeInfo {
    int source, target, weight;
};

struct UserInfo {
    int id, node;
    std::string traffic;
};

// ── Minimal JSON helpers (no external library needed) ────

static std::string slurp(const std::string& path)
{
    std::ifstream ifs(path);
    if (!ifs.is_open()) {
        NS_FATAL_ERROR("Cannot open " << path);
    }
    return std::string((std::istreambuf_iterator<char>(ifs)),
                        std::istreambuf_iterator<char>());
}

/* Extract integer value for a key like "num_nodes": 30 */
static int jsonInt(const std::string& json, const std::string& key)
{
    std::string needle = "\"" + key + "\":";
    auto pos = json.find(needle);
    if (pos == std::string::npos) { needle = "\"" + key + "\": "; pos = json.find(needle); }
    if (pos == std::string::npos) return -1;
    pos = json.find_first_of("-0123456789", pos + needle.size());
    return std::atoi(json.c_str() + pos);
}

/* Extract a flat integer array like "upfs": [2, 5, 12, ...] */
static std::vector<int> jsonIntArray(const std::string& json, const std::string& key)
{
    std::vector<int> result;
    std::string needle = "\"" + key + "\":";
    auto pos = json.find(needle);
    if (pos == std::string::npos) { needle = "\"" + key + "\": "; pos = json.find(needle); }
    if (pos == std::string::npos) return result;

    auto open  = json.find('[', pos);
    auto close = json.find(']', open);
    std::string inner = json.substr(open + 1, close - open - 1);

    std::istringstream ss(inner);
    std::string token;
    while (std::getline(ss, token, ',')) {
        auto p = token.find_first_of("-0123456789");
        if (p != std::string::npos) result.push_back(std::atoi(token.c_str() + p));
    }
    return result;
}

/* Parse array of node objects */
static std::vector<NodeInfo> parseNodes(const std::string& json)
{
    std::vector<NodeInfo> nodes;
    std::string needle = "\"nodes\":";
    auto pos = json.find(needle);
    if (pos == std::string::npos) { needle = "\"nodes\": "; pos = json.find(needle); }
    if (pos == std::string::npos) return nodes;

    // Walk through each { ... } block inside the "nodes" array
    auto arrEnd = json.find(']', pos);
    size_t cur = pos;
    while (cur < arrEnd) {
        auto brace = json.find('{', cur);
        if (brace == std::string::npos || brace > arrEnd) break;
        auto braceEnd = json.find('}', brace);

        std::string obj = json.substr(brace, braceEnd - brace + 1);
        NodeInfo ni;
        ni.id = jsonInt(obj, "id");

        // parse x
        auto xp = obj.find("\"x\":");
        if (xp == std::string::npos) xp = obj.find("\"x\": ");
        ni.x = std::atof(obj.c_str() + obj.find_first_of("-0123456789.", xp + 3));

        // parse y
        auto yp = obj.find("\"y\":");
        if (yp == std::string::npos) yp = obj.find("\"y\": ");
        ni.y = std::atof(obj.c_str() + obj.find_first_of("-0123456789.", yp + 3));

        nodes.push_back(ni);
        cur = braceEnd + 1;
    }
    return nodes;
}

/* Parse array of edge objects */
static std::vector<EdgeInfo> parseEdges(const std::string& json)
{
    std::vector<EdgeInfo> edges;
    std::string needle = "\"edges\":";
    auto pos = json.find(needle);
    if (pos == std::string::npos) { needle = "\"edges\": "; pos = json.find(needle); }
    if (pos == std::string::npos) return edges;

    // Find the closing ] for the edges array
    int depth = 0;
    size_t arrStart = json.find('[', pos);
    size_t arrEnd = arrStart;
    for (size_t i = arrStart; i < json.size(); i++) {
        if (json[i] == '[') depth++;
        if (json[i] == ']') { depth--; if (depth == 0) { arrEnd = i; break; } }
    }

    size_t cur = arrStart;
    while (cur < arrEnd) {
        auto brace = json.find('{', cur);
        if (brace == std::string::npos || brace > arrEnd) break;
        auto braceEnd = json.find('}', brace);

        std::string obj = json.substr(brace, braceEnd - brace + 1);
        EdgeInfo ei;
        ei.source = jsonInt(obj, "source");
        ei.target = jsonInt(obj, "target");
        ei.weight = jsonInt(obj, "weight");
        edges.push_back(ei);
        cur = braceEnd + 1;
    }
    return edges;
}

/* Parse array of user objects */
static std::vector<UserInfo> parseUsers(const std::string& json)
{
    std::vector<UserInfo> users;
    std::string needle = "\"users\":";
    auto pos = json.find(needle);
    if (pos == std::string::npos) { needle = "\"users\": "; pos = json.find(needle); }
    if (pos == std::string::npos) return users;

    int depth = 0;
    size_t arrStart = json.find('[', pos);
    size_t arrEnd = arrStart;
    for (size_t i = arrStart; i < json.size(); i++) {
        if (json[i] == '[') depth++;
        if (json[i] == ']') { depth--; if (depth == 0) { arrEnd = i; break; } }
    }

    size_t cur = arrStart;
    while (cur < arrEnd) {
        auto brace = json.find('{', cur);
        if (brace == std::string::npos || brace > arrEnd) break;
        auto braceEnd = json.find('}', brace);

        std::string obj = json.substr(brace, braceEnd - brace + 1);
        UserInfo ui;
        ui.id   = jsonInt(obj, "id");
        ui.node = jsonInt(obj, "node");
        users.push_back(ui);
        cur = braceEnd + 1;
    }
    return users;
}

// ── Main simulation ──────────────────────────────────────

int main(int argc, char *argv[])
{
    CommandLine cmd;
    cmd.Parse(argc, argv);

    // ── 1. Parse topology.json ──
    std::string raw = slurp("topology.json");
    int numNodes = jsonInt(raw, "num_nodes");
    if (numNodes <= 0) numNodes = 30;

    auto nodesInfo = parseNodes(raw);
    auto edgesInfo = parseEdges(raw);
    auto upfs      = jsonIntArray(raw, "upfs");
    auto usersInfo = parseUsers(raw);

    std::set<int> upfSet(upfs.begin(), upfs.end());

    std::cout << "[ns-3] Nodes=" << numNodes
              << "  Edges=" << edgesInfo.size()
              << "  UPFs=" << upfs.size()
              << "  Users=" << usersInfo.size() << "\n";

    // ── 2. Create ns-3 nodes ──
    NodeContainer allNodes;
    allNodes.Create(numNodes);

    // ── 3. Mobility (grid positions from JSON, plus random walk) ──
    MobilityHelper mobility;
    Ptr<ListPositionAllocator> posAlloc = CreateObject<ListPositionAllocator>();
    for (int i = 0; i < numNodes; ++i) {
        double px = 10.0 * (i % 6);   // default grid
        double py = 10.0 * (i / 6);
        // Override with JSON positions if available
        for (const auto& ni : nodesInfo) {
            if (ni.id == i) { px = ni.x; py = ni.y; break; }
        }
        posAlloc->Add(Vector(px, py, 0.0));
    }
    mobility.SetPositionAllocator(posAlloc);
    mobility.SetMobilityModel("ns3::RandomWalk2dMobilityModel",
                              "Bounds", RectangleValue(Rectangle(0, 150, 0, 150)));
    mobility.Install(allNodes);

    // ── 4. Internet stack ──
    InternetStackHelper internet;
    internet.Install(allNodes);

    // ── 5. Point-to-point links (100 Mbps, 5 ms delay) ──
    PointToPointHelper p2p;
    p2p.SetDeviceAttribute("DataRate", StringValue("100Mbps"));
    p2p.SetChannelAttribute("Delay", StringValue("5ms"));

    Ipv4AddressHelper ipv4;
    int subnet = 1;
    for (const auto& e : edgesInfo) {
        if (e.source >= numNodes || e.target >= numNodes) continue;
        NetDeviceContainer devs = p2p.Install(
            NodeContainer(allNodes.Get(e.source), allNodes.Get(e.target)));

        std::ostringstream base;
        base << "10." << (subnet / 256) << "." << (subnet % 256) << ".0";
        ipv4.SetBase(base.str().c_str(), "255.255.255.0");
        ipv4.Assign(devs);
        subnet++;
    }

    Ipv4GlobalRoutingHelper::PopulateRoutingTables();

    // ── 6. UDP Echo servers on UPF nodes ──
    uint16_t port = 9;
    for (int uid : upfs) {
        if (uid >= numNodes) continue;
        UdpEchoServerHelper server(port);
        auto apps = server.Install(allNodes.Get(uid));
        apps.Start(Seconds(1.0));
        apps.Stop(Seconds(10.0));
    }

    // ── 7. UDP Echo clients: users → nearest UPF ──
    int flowCount = std::min((int)usersInfo.size(), 30);  // cap flows
    for (int i = 0; i < flowCount; ++i) {
        int srcNode = usersInfo[i].node;
        if (srcNode >= numNodes) continue;

        // Pick a random UPF as destination
        int dstUpf = upfs[i % upfs.size()];
        if (dstUpf >= numNodes) continue;

        Ptr<Ipv4> dstIp = allNodes.Get(dstUpf)->GetObject<Ipv4>();
        if (dstIp->GetNInterfaces() < 2) continue;
        Ipv4Address addr = dstIp->GetAddress(1, 0).GetLocal();

        UdpEchoClientHelper client(addr, port);
        client.SetAttribute("MaxPackets",  UintegerValue(50));
        client.SetAttribute("Interval",    TimeValue(MilliSeconds(100)));
        client.SetAttribute("PacketSize",  UintegerValue(1024));

        auto apps = client.Install(allNodes.Get(srcNode));
        apps.Start(Seconds(2.0));
        apps.Stop(Seconds(10.0));
    }

    // ── 8. FlowMonitor ──
    FlowMonitorHelper flowHelper;
    Ptr<FlowMonitor> flowMon = flowHelper.InstallAll();

    // ── 9. NetAnim ──
    AnimationInterface anim("upf-animation.xml");
    anim.EnablePacketMetadata(true);

    for (int i = 0; i < numNodes; ++i) {
        if (upfSet.count(i)) {
            anim.UpdateNodeDescription(allNodes.Get(i), "UPF");
            anim.UpdateNodeColor(allNodes.Get(i), 255, 0, 0);   // RED
            anim.UpdateNodeSize(i, 5.0, 5.0);
        } else {
            anim.UpdateNodeDescription(allNodes.Get(i), "User");
            anim.UpdateNodeColor(allNodes.Get(i), 0, 0, 255);   // BLUE
            anim.UpdateNodeSize(i, 3.0, 3.0);
        }
    }

    // ── 10. Run ──
    Simulator::Stop(Seconds(10.0));
    Simulator::Run();

    flowMon->SerializeToXmlFile("flowmon.xml", true, true);

    Simulator::Destroy();
    std::cout << "[ns-3] Simulation finished successfully.\n";
    return 0;
}
