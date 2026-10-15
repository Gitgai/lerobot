# ZeroTier: laptop could not reach AI90 (2026-10-15)

Network d3ecf5726ded3c8e. AI90 = 9ffa0bb1b0 (ZT 192.168.194.220, LAN 192.168.0.103 on Wi-Fi
wlp10s0, public 73.112.168.241). Laptop = c3ae05328d (ZT .228, India). Neighbour kglenova =
9328a213cc (ZT .17, LAN 192.168.0.107, same router).

## Symptom
Laptop ping to 192.168.194.220 timed out; laptop had no peer entry for AI90. AI90
`zerotier-cli info` = OFFLINE; all four PLANET roots `RELAY -1`. LAN peers and the
controller (35.208.4.147) were DIRECT and fine. Workaround used all day:
`ssh -J kiran@192.168.194.17 kiran@192.168.0.103`.

## Facts established (all without root unless noted)
- Both nodes authorised in Central; clocks correct; planet files identical on AI90 and kglenova.
- tcpdump on AI90 (operator, root): HELLOs leave to all four roots from 3 ports every 5 s;
  no UDP reply from any root; only the controller answers.
- UDP from AI90 works in general: STUN (Google) and DNS answered; mapping is port-preserving
  (src 9993 -> public 9993). ICMP to all roots OK. UDP tracepath on port 9993 reaches all four
  roots from AI90 AND from kglenova identically -> the router/ISP path is not the difference.
- kglenova, same router and public IP, is online over plain UDP (no TCP relay) and is seen by
  the laptop DIRECT at 73.112.168.241/58250 (its secondary port, not 9993).
- AI90-only oddities: ~8.5 ICMP dest-unreachable/s received (kglenova ~0.2/s); conntrack and
  UDP rates are small on both; ufw active on AI90 but logged no blocks.
- 06:22 local: primaryPort set to 9994 in /var/lib/zerotier-one/local.conf (operator ran the
  command) + service restart. ZeroTier then fell back to its TCP relay (204.80.128.1:443),
  status TUNNELED; roots began answering sporadically over UDP (75-106 ms RTT, then quiet).
- 10:43Z: laptop reachable from AI90 again, RELAY path, ~260-310 ms. Holding as of 10:52Z.

## State
Working but degraded: AI90 is TUNNELED (TCP relay to roots), laptop path relayed, not direct.
Root cause of "roots do not answer AI90's UDP" not identified; needs root on AI90/kglenova:
  AI90:     sudo timeout 30 tcpdump -ni wlp10s0 'icmp or src host 84.17.53.155 or src host
            103.195.103.66 or src host 185.152.67.145 or src host 79.127.159.187'
  kglenova: sudo zerotier-cli info; sudo zerotier-cli peers | grep PLANET
  laptop:   tracepath -n -p 9993 -m 25 84.17.53.155 | tail -3
Candidates still open: router NAT/UPnP confusion with three ZT nodes behind one IP all
using 9993 (kglenova only works on its secondary port); root-side rate limiting of the
public IP. Not the cause: clock, planet, path, firewall logs, conntrack, wired 169.254 port.

## Tools
Token copy at ~/.zeroTierOneAuthToken/authtoken.secret (created 2026-10-14 by the operator)
lets `zerotier-cli -T"$(cat ~/.zeroTierOneAuthToken/authtoken.secret)" peers` run without sudo.
Sampler log: ~/tmp/zt_sample_1041.log. STUN probe: ~/tmp/stun_probe.py.

## Update 16:50Z — relapse, and a step of mine that made it worse
- ~12:00-16:29Z: AI90 lost its ZeroTier data plane entirely (ARP over the overlay fails to every
  member, even kglenova on the same LAN, although ZT control packets flow and peers are listed).
  kglenova itself still reaches the other two house members (.93, .235) but NOT the laptop
  (ARP FAILED) — the laptop side also appears down or on a new network.
- 16:33Z: without root the only lever was the local API: `zerotier-cli leave/join`. Result:
  network stuck in REQUESTING_CONFIGURATION with no assigned address for >15 min although the
  controller exchanges packets with AI90 every few seconds. Worse than before (had an address,
  no traffic). Not repeating it.
- Fix needs root on AI90:  sudo rm /var/lib/zerotier-one/local.conf && sudo systemctl restart zerotier-one
  Lesson: the 09:22-local primaryPort change (my suggestion) correlated with the slide into
  TUNNELED mode and then total loss; revert it first. Access path independent of ZeroTier
  (reverse SSH tunnel to a host the operator controls) proposed, awaiting approval.
