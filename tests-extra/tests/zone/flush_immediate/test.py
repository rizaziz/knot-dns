#!/usr/bin/env python3

'''With zonefile-flush: 0, test that the zonefile gets flushed immediately in various scenarios'''

from dnstest.test import Test
from dnstest.utils import *

t = Test()

master = t.server("knot")
slave = t.server("knot")
zone = t.zone_rnd(1, dnssec=False, records=10)
t.link(zone, master, slave, ixfr=True)

master.dnssec(zone).enable = True

master.zonefile_sync = 0
slave.zonefile_sync = 0

if master.valgrind:
    master.semantic_check = False
    slave.semantic_check = False

t.start()

m_zfpath = master.zones[zone[0].name].zfile.path
s_zfpath = slave.zones[zone[0].name].zfile.path

master.zones_wait(zone)
slave.zones_wait(zone)
t.sleep(2)

# check zonefile flushed after load and sign
master.zone_verify(zone)

# check zonefile flushed after AXFR
slave.zone_verify(zone)

# reload with re-sign (no additional serial increment)
master.ctl("zone-freeze", wait=True)
master.zones[zone[0].name].zfile.update_soa()
m_mtime0a = os.stat(m_zfpath).st_mtime
t.sleep(1)
master.reload()
t.sleep(10)
m_mtime0b = os.stat(m_zfpath).st_mtime
master.ctl("zone-thaw", wait=True)

t.sleep(4)

# DDNS test
m_mtime1 = os.stat(m_zfpath).st_mtime
s_mtime1 = os.stat(s_zfpath).st_mtime

up = master.update(zone)
up.add("djojdw", 3600, "TXT", "this wont sure be there yet")
up.send("NOERROR")

t.sleep(4)

m_mtime2 = os.stat(m_zfpath).st_mtime
s_mtime2 = os.stat(s_zfpath).st_mtime

# check zonefile not flushed after reload with re-sign when frozen
if m_mtime0a != m_mtime0b:
    set_err("Flushed after reload with re-sign when frozen")

# check zonefile flushed after reload with re-sign after thawed
if m_mtime1 == m_mtime0a:
    set_err("Not flushed after reload with re-sign")

# check zonefile flushed after DDNS
if m_mtime2 == m_mtime1:
    set_err("Not flushed after DDNS")

# check zonefile flushed after IXFR
if s_mtime2 == s_mtime1:
    set_err("Not flushed after IXFR")

master.stop()
master.start()
master.zones_wait(zone)
t.sleep(1)
m_mtime3 = os.stat(m_zfpath).st_mtime

# check zonefile not re-flushed after restart
if m_mtime3 != m_mtime2:
    set_err("Up-to-date re-flushed after restart")

t.end()

