# Packet Tracer saved-file XML schema (observed, PT 6.1–8.2 era files)

This is the distilled, empirically-verified knowledge from decrypting the ~260
sample files shipped with Packet Tracer 8.2 and successfully generating a file
that PT 8.2 opens. Treat it as ground truth for structure, but always mine a
fresh reference for the specific device model you need.

## Document skeleton

```xml
<PACKETTRACER5>
 <VERSION>6.1.0.0026</VERSION>          <!-- keep the reference's value; PT 8.2 silently upgrades old versions -->
 <NETWORK>
  <DEVICES>
   <DEVICE> ... </DEVICE>               <!-- one per device; ORDER defines the indexes used by LINKS -->
  </DEVICES>
  <LINKS>
   <LINK> ... </LINK>
  </LINKS>
  <SHAPETESTS/>
  <DESCRIPTION/>
 </NETWORK>
 <SCENARIOSET>...</SCENARIOSET>
 <OPTIONS>...</OPTIONS>                  <!-- language/UI prefs; keep from reference -->
 <PHYSICALWORKSPACE>                     <!-- physical-view containers + the logical workspace NOTES -->
  ... <BUILDING_GRID/> <GRID_COLOR/> ...
  <NOTES><NOTE uuid="{...}">...</NOTE></NOTES>
 </PHYSICALWORKSPACE>
 <FILTERS .../>                          <!-- protocol list; keep from reference -->
 <CLUSTERS><ROOTCLUSTER>...</ROOTCLUSTER></CLUSTERS>
 <LINES/> <RECTANGLES/> <ELLIPSES/> <POLYGONS/>
 <USER_PROFILE>...</USER_PROFILE>
 <MULTIUSER>...</MULTIUSER>
</PACKETTRACER5>
```

Root element is `PACKETTRACER5` even in PT 8.2. Device templates (.ptd) use
`<PACKETTRACER templateType="COMPONENT" ...>` instead and contain only
TYPE/MODEL stubs — PT expands their ports from an internal database at
instantiation, so you cannot learn PORT field details from .ptd files; clone
PORT elements from *saved* .pkt files instead.

## DEVICE element (field order as PT writes it)

```
DEVICE
  ENGINE
    TYPE customModel="" model="2811"  -> text "Router"      # model string must match PT's palette name
    NAME translate="true"  Router0                          # display name
    POWER true                                              # device power state
    DESCRIPTION (empty)
    MODULE ... (see module tree below)
    CUSTOM_VARS          AAAAAA==                           # opaque base64; copy from reference
    CUSTOM_INTERFACE / SYS_CONTACT / SYS_LOCATION (empty)
    COORD_SETTINGS       X_COORD/Y_COORD/Z_COORD            # physical-view coords; copy from reference
    SYS_NAME             Router                             # IOS hostname; keep consistent with config `hostname`
    RUNNINGCONFIG        <LINE>...</LINE>*                  # plain-text running config, one line per element
    STARTUPCONFIG        (usually empty <STARTUPCONFIG/>)
    CURRENT_COMMAND_SET  2800_advip_12.4                    # must match the model's IOS
    FILE_MANAGER         flash: with IOS .bin + sigdef files
    CONFIG_REGISTER / NEXT_CONFIG_REGISTER   8450 (0x2102)
    CURRENT_BOOT_FILE    flash:/c2800nm-advipservicesk9-mz.124-15.T1.bin
    BUILD_IN_ADDR        base MAC
    SECURITY / ALGORITHM_SETTINGS / SERIALNUMBER
    VLANS (1,1002-1005 defaults) / VTP / SIG_IPSPROCESS
  WORKSPACE
    LOGICAL
      X / Y              # logical-workspace position (what you see on canvas)
      DEVCLUSTERID       1-1
      CUSTOM_IMAGE_PHYSICAL / CUSTOM_IMAGE_LOGICAL (empty)
      MEM_ADDR / DEV_ADDR        # stale internal addresses are tolerated by PT
    PHYSICAL translate="true"  Intercity,Home City,Corporate Office,Main Wiring Closet,Rack,Router0
```

Model-specific command sets / IOS observed:
| model | CURRENT_COMMAND_SET | flash .bin | CAPACITY |
|-------|--------------------|------------|----------|
| 1841  | 1841_advip_12.4    | c1841-advipservicesk9-mz.124-15.T1.bin | 64016384 |
| 2811  | 2800_advip_12.4    | c2800nm-advipservicesk9-mz.124-15.T1.bin | 64016384 |

## MODULE / SLOT tree (2811 example)

```xml
<MODULE>                                    <!-- chassis -->
  <TYPE>eNonRemovableModule</TYPE><MODEL/>
  <SLOT>
    <TYPE>eNonRemovableModule</TYPE>        <!-- motherboard -->
    <MODULE>
      <TYPE>eNonRemovableModule</TYPE><MODEL/>
      <SLOT><TYPE>eInterfaceCard</TYPE></SLOT>   <!-- 4 WIC slots; empty or contain a module -->
      ... x4
      <PORT> ... FastEthernet0/0 ... </PORT>     <!-- onboard ports serialize directly -->
      <PORT> ... FastEthernet0/1 ... </PORT>     <!-- under the motherboard MODULE -->
    </MODULE>
  </SLOT>
  <SLOT>
    <TYPE>eNetworkModule</TYPE>             <!-- NM slot -->
    <MODULE>
      <TYPE>eNetworkModule</TYPE>
      <MODEL>NM-8A/S</MODEL>                <!-- module model exactly as in PT's palette -->
      <PORT> ... Serial1/0 ... </PORT>      <!-- module ports serialize inside the module -->
      ... (NM-8A/S has 8: Serial1/0..Serial1/7, TYPE eSmartSerial, BANDWIDTH 128)
    </MODULE>
  </SLOT>
</MODULE>
```

**Port names are NOT stored anywhere** — PT derives them from slot position
(NM slot 1 -> `Serial1/x`, WIC slot 0 -> `Serial0/0/x`). The `<PORT>Serial1/0</PORT>`
strings inside `<LINK><CABLE>` must therefore match what the slot hierarchy
implies, or the link fails to bind.

## PORT element (complete field list, in order)

```
TYPE eSmartSerial | eCopperFastEthernet | eCopperGigabitEthernet | ...
POWER true|false                          # physical link state; keep consistent with `shutdown` in config
PINS false
BANDWIDTH 128 | 1544 | 100000 | ...       # Kbit; NM-8A/S=128, WIC-2T/HWIC-2T=1544, FE=100000
FULLDUPLEX true|false
AUTONEGOTIATEBANDWIDTH true
AUTONEGOTIATEDUPLEX true
MACADDRESS / BIA                          # XXXX.XXXX.XXXX; make unique per port
CLOCKRATE 2000000                         # serial DCE side: must match config `clock rate`
CLOCKRATEFLAG false
DESCRIPTION /
CHANNEL 0
IP / SUBNET                               # must match config `ip address`/`ip address ... secondary` none
PORT_GATEWAY / PORT_DNS /
PORT_DHCP_ENABLE false
ND_SUPPRESSED false
TIMEOUT 14400000
PC_FIREWALL false / PC_IPV6_FIREWALL false
IPV6_ENABLED false / IPV6_ADDRESS_AUTOCONFIG false
IPV6_PORT_GATEWAY / PORT_DNS /
IPV6_LINK_LOCAL /
IPV6_DEFAULT_LINK_LOCAL FE80::...         # EUI-64 of the MAC (flip bit7, insert FFFE); cosmetic but keep correct
IPV6_PORT_AUTO_CONFIG_ENABLED false
IPV6_PORT_DHCP_ENABLED false
IPV6_ADDRESSES /
```

## LINK element

```xml
<LINK>
  <TYPE>eSerial</TYPE>                    <!-- eSerial for serial DCE/DTE copper; eCopperFastEthernet etc. otherwise -->
  <CABLE>
    <LENGTH>0</LENGTH>
    <FROM>0</FROM>                        <!-- DEVICE index (0-based, order in DEVICES) -->
    <PORT>Serial1/0</PORT>                <!-- port name as derived from slot tree -->
    <TO>1</TO>
    <PORT>Serial1/0</PORT>
    <FROM_DEVICE_MEM_ADDR>...</FROM_DEVICE_MEM_ADDR>   <!-- stale values are tolerated -->
    <TO_DEVICE_MEM_ADDR>...</TO_DEVICE_MEM_ADDR>
    <FROM_PORT_MEM_ADDR>...</FROM_PORT_MEM_ADDR>
    <TO_PORT_MEM_ADDR>...</TO_PORT_MEM_ADDR>
    <DCEDEV>0</DCEDEV>                    <!-- which side is DCE -->
    <DCEPORT>Serial1/0</DCEPORT>
  </CABLE>
</LINK>
```

In the topology view a serial cable always draws as a red lightning bolt —
that is its normal look, not an error. Port link-lights (green triangles) show
physical layer state only; line protocol (PPP LCP) is not visible there.

## NOTES (logical workspace annotations)

Lives inside `<PHYSICALWORKSPACE>` at the end:

```xml
<NOTES>
  <NOTE uuid="{guid}">
    <X>236</X><Y>148</Y><Z>40000</Z>
    <TEXT translate="true">IP地址：10.0.0.1&#10;子网掩码：255.255.255.252</TEXT>
    <NOTECLUSTERID>1-1</NOTECLUSTERID>
  </NOTE>
</NOTES>
```

## Consistency invariants (the actual correctness contract)

PT reconciles the XML into a live simulation at load. It does not hard-fail on
every inconsistency — some silently break the network instead, which is worse.
Before encrypting, verify:

1. `LINKS` FROM/TO indexes match the DEVICE order; PORT names match the slot tree.
2. Per port: `IP`/`SUBNET` ↔ config `ip address` line; `POWER` ↔ presence of
   `shutdown`; `CLOCKRATE` (DCE side) ↔ config `clock rate` line.
3. `SYS_NAME` ↔ config `hostname`.
4. `CURRENT_COMMAND_SET`, `CURRENT_BOOT_FILE`, flash `.bin` `<SET_NAME>` all
   match the engine model.
5. `username`/`ppp authentication chap`/`encapsulation ppp` exist ONLY as
   config text — both ends of a link must agree on encapsulation or LCP never
   opens.
6. MAC addresses unique per port; `IPV6_DEFAULT_LINK_LOCAL` derived from them.
7. Device hostname: a fresh PT router's IOS hostname is `Router` (prompt
   `Router>`), NOT the display name (`Router0`). CHAP needs
   `username <peer-hostname> password <pw>` on each side, so set explicit
   hostnames.

## Behaviors observed in PT 8.2 (Windows)

- Launching `PacketTracer.exe <file>` while another instance runs spawns a NEW
  process; the file loads in the new one.
- Files with an older `<VERSION>` (e.g. 6.1.0.0026) open silently and are
  upgraded on save.
- Single click selects a device; double click opens its config window (a
  separate top-level window).
- 19 of 263 shipped sample .pkt files fail decryption (extra appended
  sections). Expect some failures when bulk-decrypting references.
- The default 2811 placed from the palette has no WIC/NM modules; serial
  interfaces only exist after inserting a module.
