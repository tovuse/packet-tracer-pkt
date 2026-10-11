"""Worked example: generator for the PPP-with-CHAP lab (Experiment 1-1).

Verbatim script from a verified real run (Windows, PT 8.2): the generated file
opened in Packet Tracer with the intended topology and configs. It reads its
decrypted reference from a fixed relative path -- adapt the paths and follow
SKILL.md for the full workflow (mine refs -> edit -> encrypt -> validate).

Target topology (per the course PPT):
  Router0 2811 + NM-8A/S, Se1/0 = 10.0.0.1/30, DCE
  Router1 2811 + NM-8A/S, Se1/0 = 10.0.0.2/30
  serial back-to-back, encapsulation ppp + CHAP (username/hostname), clock rate on DCE.
"""
import ipaddress
import re

BASE = open("refs/01 Networking_OSPF_ospf_network_lo_p2p.pkt.xml", encoding="utf-8").read()

# ---------------------------------------------------------------- helpers

def mac_prefix(prefix_bytes, idx):
    """prefix_bytes: first 5 octets; idx: 6th octet."""
    b = bytes(prefix_bytes) + bytes([idx])
    return f"{b[0]:02X}{b[1]:02X}.{b[2]:02X}{b[3]:02X}.{b[4]:02X}{b[5]:02X}"


def linklocal(m):
    b = bytes.fromhex(m.replace(".", ""))
    eui = b[:3] + b"\xff\xfe" + b[3:]
    eui = bytes([eui[0] ^ 0x02]) + eui[1:]
    v6 = ipaddress.IPv6Address(b"\xfe\x80" + b"\x00" * 6 + eui)
    return str(v6).upper()


def port_xml(ptype, m, power, ip="", subnet="", bandwidth=None, clockrate=2000000):
    bw = {"eSmartSerial": 128, "eCopperFastEthernet": 100000}[ptype] if bandwidth is None else bandwidth
    return f"""<PORT>
         <TYPE>{ptype}</TYPE>
         <POWER>{'true' if power else 'false'}</POWER>
         <PINS>false</PINS>
         <BANDWIDTH>{bw}</BANDWIDTH>
         <FULLDUPLEX>{'false' if ptype == 'eCopperFastEthernet' else 'true'}</FULLDUPLEX>
         <AUTONEGOTIATEBANDWIDTH>true</AUTONEGOTIATEBANDWIDTH>
         <AUTONEGOTIATEDUPLEX>true</AUTONEGOTIATEDUPLEX>
         <MACADDRESS>{m}</MACADDRESS>
         <BIA>{m}</BIA>
         <CLOCKRATE>{clockrate}</CLOCKRATE>
         <CLOCKRATEFLAG>false</CLOCKRATEFLAG>
         <DESCRIPTION/>
         <CHANNEL>0</CHANNEL>
         <IP>{ip}</IP>
         <SUBNET>{subnet}</SUBNET>
         <PORT_GATEWAY/>
         <PORT_DNS/>
         <PORT_DHCP_ENABLE>false</PORT_DHCP_ENABLE>
         <ND_SUPPRESSED>false</ND_SUPPRESSED>
         <TIMEOUT>14400000</TIMEOUT>
         <PC_FIREWALL>false</PC_FIREWALL>
         <PC_IPV6_FIREWALL>false</PC_IPV6_FIREWALL>
         <IPV6_ENABLED>false</IPV6_ENABLED>
         <IPV6_ADDRESS_AUTOCONFIG>false</IPV6_ADDRESS_AUTOCONFIG>
         <IPV6_PORT_GATEWAY/>
         <IPV6_PORT_DNS/>
         <IPV6_LINK_LOCAL/>
         <IPV6_DEFAULT_LINK_LOCAL>{linklocal(m)}</IPV6_DEFAULT_LINK_LOCAL>
         <IPV6_PORT_AUTO_CONFIG_ENABLED>false</IPV6_PORT_AUTO_CONFIG_ENABLED>
         <IPV6_PORT_DHCP_ENABLED>false</IPV6_PORT_DHCP_ENABLED>
         <IPV6_ADDRESSES/>
        </PORT>"""


def running_config(dev_no, peer):
    """dev_no: 0 or 1; peer: other router hostname."""
    ip = "10.0.0.1" if dev_no == 0 else "10.0.0.2"
    lines = ["!", "version 12.4", "no service timestamps log datetime msec",
             "no service timestamps debug datetime msec", "no service password-encryption",
             "!", f"hostname Router{dev_no}", "!", "!", "!", "!", "!", "!", "!",
             "ip cef", "no ipv6 cef"]
    lines += ["!"] * 12
    lines += ["spanning-tree mode pvst", "!", "!", "!", "!",
              f"username Router{peer} password cisco", "!"]
    lines += ["interface FastEthernet0/0", " no ip address", " duplex auto", " speed auto", " shutdown", "!",
              "interface FastEthernet0/1", " no ip address", " duplex auto", " speed auto", " shutdown", "!",
              "interface Serial1/0", f" ip address {ip} 255.255.255.252", " encapsulation ppp",
              " ppp authentication chap"]
    if dev_no == 0:
        lines.append(" clock rate 2000000")
    lines.append("!")
    for i in range(1, 8):
        lines += [f"interface Serial1/{i}", " no ip address", " shutdown", "!"]
    lines += ["interface Vlan1", " no ip address", " shutdown", "!",
              "ip classless", "!", "ip flow-export version 9"]
    lines += ["!"] * 7
    lines += ["line con 0", "!", "line aux 0", "!", "line vty 0 4", " login", "!", "!", "!", "end"]
    return "\n".join(f"      <LINE>{l}</LINE>" for l in lines)


def device(name, dev_no, x, y, mem_addr, dev_addr, prefix):
    """prefix: 2 bytes for port MACs."""
    ports = []
    # onboard FastEthernet0/0, 0/1 (shutdown)
    ports.append(port_xml("eCopperFastEthernet", mac_prefix(prefix, 1), False))
    ports.append(port_xml("eCopperFastEthernet", mac_prefix(prefix, 2), False))
    # NM-8A/S: 8 smart-serial ports Serial1/0..1/7
    se_ports = []
    for i in range(8):
        ip = subnet = ""
        power = False
        clock = 2000000
        if i == 0:
            ip = "10.0.0.1" if dev_no == 0 else "10.0.0.2"
            subnet = "255.255.255.252"
            power = True
        se_ports.append(port_xml("eSmartSerial", mac_prefix(prefix, 3 + i), power, ip, subnet,
                                 clockrate=clock))
    module_tree = f"""<MODULE>
      <TYPE>eNonRemovableModule</TYPE>
      <MODEL/>
      <SLOT>
       <TYPE>eNonRemovableModule</TYPE>
       <MODULE>
        <TYPE>eNonRemovableModule</TYPE>
        <MODEL/>
        <SLOT>
         <TYPE>eInterfaceCard</TYPE>
        </SLOT>
        <SLOT>
         <TYPE>eInterfaceCard</TYPE>
        </SLOT>
        <SLOT>
         <TYPE>eInterfaceCard</TYPE>
        </SLOT>
        <SLOT>
         <TYPE>eInterfaceCard</TYPE>
        </SLOT>
        {ports[0]}
        {ports[1]}
       </MODULE>
      </SLOT>
      <SLOT>
       <TYPE>eNetworkModule</TYPE>
       <MODULE>
        <TYPE>eNetworkModule</TYPE>
        <MODEL>NM-8A/S</MODEL>
        {se_ports[0]}
        {se_ports[1]}
        {se_ports[2]}
        {se_ports[3]}
        {se_ports[4]}
        {se_ports[5]}
        {se_ports[6]}
        {se_ports[7]}
       </MODULE>
      </SLOT>
     </MODULE>"""

    base_mac = mac_prefix(prefix, 0)
    peer = 1 - dev_no
    return f"""<DEVICE>
    <ENGINE>
     <TYPE customModel="" model="2811">Router</TYPE>
     <NAME translate="true">{name}</NAME>
     <POWER>true</POWER>
     <DESCRIPTION></DESCRIPTION>
     {module_tree}
     <CUSTOM_VARS>AAAAAA==</CUSTOM_VARS>
     <CUSTOM_INTERFACE></CUSTOM_INTERFACE>
     <SYS_CONTACT></SYS_CONTACT>
     <SYS_LOCATION></SYS_LOCATION>
     <COORD_SETTINGS>
      <X_COORD>1918.54</X_COORD>
      <Y_COORD>1918.54</Y_COORD>
      <Z_COORD>0</Z_COORD>
     </COORD_SETTINGS>
     <SYS_NAME>{name}</SYS_NAME>
     <RUNNINGCONFIG>
{running_config(dev_no, peer)}
     </RUNNINGCONFIG>
     <STARTUPCONFIG/>
     <CURRENT_COMMAND_SET>2800_advip_12.4</CURRENT_COMMAND_SET>
     <FILE_MANAGER>
      <FILE class="CDirectory">
       <FILE_NUMBER>0</FILE_NUMBER>
       <NAME></NAME>
       <DATE_TIME>0</DATE_TIME>
       <PERMISSION>6</PERMISSION>
       <FILE_CONTENT/>
       <FILES>
        <FILE class="CFileSystem">
         <FILE_NUMBER>0</FILE_NUMBER>
         <NAME>flash:</NAME>
         <DATE_TIME>0</DATE_TIME>
         <PERMISSION>6</PERMISSION>
         <FILE_CONTENT/>
         <FILES>
          <FILE class="CFile">
           <FILE_NUMBER>3</FILE_NUMBER>
           <NAME>c2800nm-advipservicesk9-mz.124-15.T1.bin</NAME>
           <DATE_TIME>0</DATE_TIME>
           <PERMISSION>6</PERMISSION>
           <FILE_CONTENT class="CIosFileContent">
            <DEVICE_TYPE>Router</DEVICE_TYPE>
            <SET_NAME>2800_advip_12.4</SET_NAME>
           </FILE_CONTENT>
          </FILE>
          <FILE class="CFile">
           <FILE_NUMBER>2</FILE_NUMBER>
           <NAME>sigdef-category.xml</NAME>
           <DATE_TIME>0</DATE_TIME>
           <PERMISSION>6</PERMISSION>
           <FILE_CONTENT class="CIpsCategoryFileContent">
            <SIG_CAT/>
           </FILE_CONTENT>
          </FILE>
          <FILE class="CFile">
           <FILE_NUMBER>1</FILE_NUMBER>
           <NAME>sigdef-default.xml</NAME>
           <DATE_TIME>0</DATE_TIME>
           <PERMISSION>6</PERMISSION>
           <FILE_CONTENT class="CIpsDatFileContent">
            <ICMP_SIGNATURE>
             <SIGNATURE>
              <SIG_ID>2004</SIG_ID>
              <SUB_ID>0</SUB_ID>
              <RETIRED>0</RETIRED>
              <ENABLED>0</ENABLED>
              <EVENT_ACTION>0</EVENT_ACTION>
             </SIGNATURE>
            </ICMP_SIGNATURE>
           </FILE_CONTENT>
          </FILE>
         </FILES>
         <FILE_COUNTER>3</FILE_COUNTER>
         <CAPACITY>64016384</CAPACITY>
        </FILE>
       </FILES>
      </FILE>
     </FILE_MANAGER>
     <CONFIG_REGISTER>8450</CONFIG_REGISTER>
     <NEXT_CONFIG_REGISTER>8450</NEXT_CONFIG_REGISTER>
     <CURRENT_BOOT_FILE>flash:/c2800nm-advipservicesk9-mz.124-15.T1.bin</CURRENT_BOOT_FILE>
     <BUILD_IN_ADDR>{base_mac}</BUILD_IN_ADDR>
     <SECURITY>
      <KEY_NAME></KEY_NAME>
      <TEMP_KEY_NAME></TEMP_KEY_NAME>
      <RSA_KEY></RSA_KEY>
      <TEMP_RSA_KEY></TEMP_RSA_KEY>
      <TIME_DATE></TIME_DATE>
      <ENABLED>0</ENABLED>
      <MODULUS_BITS>0</MODULUS_BITS>
     </SECURITY>
     <ALGORITHM_SETTINGS>
      <USE_GLOBAL>true</USE_GLOBAL>
      <CBAC_HALF_OPEN_SESSION_MULTIPLIER>1</CBAC_HALF_OPEN_SESSION_MULTIPLIER>
      <TCP_MAX_CONNECTING_SESSIONS>100</TCP_MAX_CONNECTING_SESSIONS>
      <TCP_MAX_OPENED_SESSIONS>1000</TCP_MAX_OPENED_SESSIONS>
      <INTERFACE_QUEUE_SIZE>10</INTERFACE_QUEUE_SIZE>
      <STORM_CONTROL_MULTIPLIER>10</STORM_CONTROL_MULTIPLIER>
      <TCP_MAX_RETRANSMISSION_TIMEOUT>1000</TCP_MAX_RETRANSMISSION_TIMEOUT>
     </ALGORITHM_SETTINGS>
     <SERIALNUMBER>FTX111{dev_no}J1ZX{dev_no}</SERIALNUMBER>
     <VLANS>
      <VLAN number="1" name="default"/>
      <VLAN number="1002" name="fddi-default"/>
      <VLAN number="1003" name="token-ring-default"/>
      <VLAN number="1004" name="fddinet-default"/>
      <VLAN number="1005" name="trnet-default"/>
     </VLANS>
     <VTP>
      <DOMAIN_NAME></DOMAIN_NAME>
      <MODE>0</MODE>
      <VERSION>1</VERSION>
      <PASSWORD></PASSWORD>
      <CONFIG_REVISION>0</CONFIG_REVISION>
      <UPDATER_IP>0.0.0.0</UPDATER_IP>
      <UPDATE_TIMESTAMP>0-0-00 00:00:00</UPDATE_TIMESTAMP>
     </VTP>
     <SIG_IPSPROCESS>
      <SIGNATURE>
       <SIG_ID>2004</SIG_ID>
       <SUB_ID>0</SUB_ID>
       <RETIRED>0</RETIRED>
       <ENABLED>0</ENABLED>
       <EVENT_ACTION>0</EVENT_ACTION>
      </SIGNATURE>
     </SIG_IPSPROCESS>
    </ENGINE>
    <WORKSPACE>
     <LOGICAL>
      <X>{x}</X>
      <Y>{y}</Y>
      <DEVCLUSTERID>1-1</DEVCLUSTERID>
      <CUSTOM_IMAGE_PHYSICAL></CUSTOM_IMAGE_PHYSICAL>
      <CUSTOM_IMAGE_LOGICAL></CUSTOM_IMAGE_LOGICAL>
      <MEM_ADDR>{mem_addr}</MEM_ADDR>
      <DEV_ADDR>{dev_addr}</DEV_ADDR>
     </LOGICAL>
     <PHYSICAL translate="true">Intercity,Home City,Corporate Office,Main Wiring Closet,Rack,{name}</PHYSICAL>
    </WORKSPACE>
   </DEVICE>"""


def note(uuid, x, y, z, text):
    return f"""   <NOTE uuid="{uuid}">
    <X>{x}</X>
    <Y>{y}</Y>
    <Z>{z}</Z>
    <TEXT translate="true">{text}</TEXT>
    <NOTECLUSTERID>1-1</NOTECLUSTERID>
   </NOTE>"""


# ---------------------------------------------------------------- assemble

dev0 = device("Router0", 0, 350.0, 260.0, 214091584, 328631656, bytes([0x00, 0xE0, 0xB0, 0xA0, 0x01]))
dev1 = device("Router1", 1, 700.0, 260.0, 212814292, 328362676, bytes([0x00, 0xE0, 0xB0, 0xA0, 0x11]))

links = """<LINKS>
   <LINK>
    <TYPE>eSerial</TYPE>
    <CABLE>
     <LENGTH>0</LENGTH>
     <FROM>0</FROM>
     <PORT>Serial1/0</PORT>
     <TO>1</TO>
     <PORT>Serial1/0</PORT>
     <FROM_DEVICE_MEM_ADDR>214091584</FROM_DEVICE_MEM_ADDR>
     <TO_DEVICE_MEM_ADDR>328631656</TO_DEVICE_MEM_ADDR>
     <FROM_PORT_MEM_ADDR>328362676</FROM_PORT_MEM_ADDR>
     <TO_PORT_MEM_ADDR>212814244</TO_PORT_MEM_ADDR>
     <DCEDEV>0</DCEDEV>
     <DCEPORT>Serial1/0</DCEPORT>
    </CABLE>
   </LINK>
  </LINKS>"""

notes = f"""<NOTES>
{note("{a1b2c3d4-0001-4a6b-8c2d-101112131415}", 236, 148, 40000, "IP地址：&#160;&#160;&#160;&#160; 10.0.0.1&#10;子网掩码：255.255.255.252")}
{note("{a1b2c3d4-0002-4a6b-8c2d-101112131415}", 596, 148, 40000, "IP地址：&#160;&#160;&#160;&#160; 10.0.0.2&#10;子网掩码：255.255.255.252")}
{note("{a1b2c3d4-0003-4a6b-8c2d-101112131415}", 408, 196, 40000, "Se1/0")}
{note("{a1b2c3d4-0004-4a6b-8c2d-101112131415}", 560, 196, 40000, "Se1/0")}
  </NOTES>"""

xml = BASE

# replace the two DEVICE blocks
d1 = xml.find("<DEVICE>")
d2 = xml.find("<DEVICE>", d1 + 1)
d3 = xml.find("</DEVICES>")
xml = xml[:d1] + dev0 + "\n   " + dev1 + "\n  " + xml[d3:]

# replace LINKS block
l1 = xml.find("<LINKS>")
l2 = xml.find("</LINKS>") + len("</LINKS>")
xml = xml[:l1] + links + xml[l2:]

# replace NOTES block
n1 = xml.find("<NOTES>")
n2 = xml.find("</NOTES>") + len("</NOTES>")
xml = xml[:n1] + notes + xml[n2:]

# sanity
assert 'model="1841"' not in xml
assert xml.count("<DEVICE>") == 2
assert "Serial0/0/0" not in xml

open("ppp_exp.xml", "w", encoding="utf-8").write(xml)
print("XML written:", len(xml), "bytes")

# well-formedness check
import xml.etree.ElementTree as ET
ET.fromstring(xml)
print("well-formed: OK")
