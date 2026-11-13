import base64

def varint(n):
    out = b""
    while True:
        b = n & 0x7f; n >>= 7
        out += bytes([b | (0x80 if n else 0)])
        if not n: return out

def ld(field, payload):
    if isinstance(payload, str): payload = payload.encode()
    return varint(field << 3 | 2) + varint(len(payload)) + payload

def vi(field, n):
    return varint(field << 3) + varint(n)

def airport(code): return ld(2, code)

def flight_data(date, frm, to):
    return ld(2, date) + ld(13, airport(frm)) + ld(14, airport(to))

# Passenger enum: ADULT=1, CHILD=2
PAX = [1,1,1,2]

def tfs(date, frm="CAN", to="SYD", seat=1, trip=2, pax=PAX):
    info = ld(3, flight_data(date, frm, to)) + b"".join(vi(8, p) for p in pax) + vi(9, seat) + vi(19, trip)
    return base64.b64encode(info).decode()

def tfs_rt(dep, ret, frm="CAN", to="SYD", seat=1, pax=PAX):
    info = (ld(3, flight_data(dep, frm, to)) + ld(3, flight_data(ret, to, frm))
            + b"".join(vi(8, p) for p in pax) + vi(9, seat) + vi(19, 1))
    return base64.b64encode(info).decode()
