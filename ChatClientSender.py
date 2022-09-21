import socket
import struct
import sys


# make a header and add it to the data
# header: checksum(2 bytes), seq# 4 bytes, (total data left, offset, len of data)-4 bytes, 18 bytes in total
def make_packet(seq_num, data, total_data_left, offset):
    len_data = len(data)

    udp_header = struct.pack(
        "!IIII", seq_num, total_data_left, offset, len_data
    )
    data = udp_header + data
    chksm = checksum(data)

    k = struct.pack("!H", chksm) + data

    return k

def checksum(data):
    c = int()
    for i in range(0, len(data), 2):
        bits = data[i : i + 2]
        if len(bits) == 1:
            c += int((struct.unpack("!B", bits)[0]))
        else:
            c += struct.unpack("!H", bits)[0]

        c = (c >> 16) + (~0b10000000000000000 & c)
    return c

def transmit_packet(total_data, seq_number, udp_socket, output_file):
    first_index = seq_number*1600
    last_index =  first_index + 1600
    segment_data = total_data[first_index:last_index]
    if(seq_number == 0):
        segment_data += ("EOF12" + output_file).encode()
    send_packet = make_packet(seq_number, segment_data, len(total_data), first_index)
    udp_socket.send(send_packet)

def isCorrupt(data):
    reciver_cksum = checksum(data[2:])
    print(reciver_cksum)
    sender_chksum = struct.unpack('!H', data[0:2])[0]
    print(sender_chksum)
    print(reciver_cksum == sender_chksum)
    return reciver_cksum != sender_chksum

def main():
    data = bytes()
    client_ip = str(sys.argv[2])
    client_port = int(sys.argv[4])
    
    output_file = ""
    file=''
    
    if len(sys.argv) == 8:
        file = sys.argv[6]
        output_file = sys.argv[-1]
    else:
        file = -1
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.connect((client_ip, client_port))

    if file != -1:
        with open(file, "rb") as f:
            data = f.read()
    else:
        x = input()
        data = x.encode()

    
    udp_socket.send("NAME UniMineSend".encode())
    udp_socket.recv(100)
    udp_socket.send("CONN UniMineRecv".encode())
    udp_socket.recv(100)
    udp_socket.settimeout(0.2)
    
    seq_number = 0
    ack_list = list()
    ack_list.append((255, -1))
    start = True

    total_packets = (len(data)/1600)
    window = 4
    base = 0  # increments by 1 if a right ack is recieved

    ack_data = bytes()

    #udp_socket.setblocking(False)
   

    while True:
        
        # check if EOF, base only updates after ACK's
        if(base*1600 >= len(data)):
            break
        # if(start):
        #     if len(data) < 1600:
        #         transmit_packet(data, seq_number, udp_socket, output_file)
        #     else:
        #         for i in range(window):
        #             if(i >= total_packets):
        #                 break
        #             print('seq Transmitted', seq_number)
        #             transmit_packet(data, seq_number, udp_socket, output_file)
        #             seq_number += 1
        #     start = False

        # else:
        if(seq_number < base + window and seq_number < total_packets):
            transmit_packet(data, seq_number, udp_socket, output_file)
            print('transmitting, in else seq: ', seq_number)
            seq_number += 1
        
        try:
            
            ack_data = udp_socket.recv(10)
            print(ack_data)
            if(isCorrupt(ack_data)):
                continue
            ack_tuple = struct.unpack("!BI", ack_data[2:])
            print(ack_data, " -> acklist", ack_list, "\n")
            if len(ack_list) == 0:
                ack_list.append(ack_tuple)
                base += 1
            elif ack_tuple[1] - 1 == ack_list[len(ack_list) - 1][1]:
                ack_list.append(ack_tuple)
                base += 1
            else:
                if(ack_tuple[1] > ack_list[-1][1]):
                    ack_list.append(ack_tuple)
                    base = ack_tuple[1] + 1
                
        except socket.timeout:
            seq_number = base
            if(base >= total_packets):
                break
            for i in range(base, window+base):
                print('retransmitting seq', seq_number)
                if(i >= total_packets):
                    break
                transmit_packet(data, seq_number, udp_socket, output_file)
                seq_number += 1
            print()

    udp_socket.send(".".encode())
    udp_socket.send("QUIT".encode())

main()
