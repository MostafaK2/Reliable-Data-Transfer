import socket
import struct
import sys


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


def output_to_file(data, filename):
    with open(filename, "wb") as f:
        f.write(data)


def transmitAck(seq_num, udp_socket):
    pckt = struct.pack("!BI", 0xFF, seq_num)
    chks = struct.pack("!H", checksum(pckt))
    pckt = chks + pckt
    udp_socket.send(pckt)


def main():

    file = ""

    data = bytes()
    client_ip = str(sys.argv[2])
    client_port = int(sys.argv[4])
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.connect((client_ip, client_port))

    udp_socket.send("NAME UniMineRecv".encode())
    udp_socket.recv(100)
    udp_socket.send("CONN UniMineSend".encode())
    udp_socket.recv(100)
    udp_socket.settimeout(0.2)

    seq_list = list()
    seq_list.append(-1)
    temp_data = bytes()
    start = True
    total = 1

    while total > 0:

        # this does it for only one packet
        while True:
            temp_data = bytes()
            try:
                temp_data = udp_socket.recv(2048)

                sender_checksum = struct.unpack("!H", temp_data[0:2])[0]
                reciever_checksum = checksum(temp_data[2:])
                # print('the total data left: ', total)
                # ACK break only if its ACK
                if sender_checksum == reciever_checksum:
                    seq_num = struct.unpack("!I", temp_data[2:6])[0]
                    # print('seq number', seq_num)
                    # print('seq list:', seq_list, '\n')
                    if seq_num != seq_list[-1] + 1:
                        continue

                    if start and seq_num == 0:
                        total = struct.unpack("!I", temp_data[6:10])[0]
                        seq_list.append(seq_num)

                        file_data = temp_data.split(b"EOF12")[-1]

                        file = file_data.decode()

                        # length of EOF12 is 5
                        index = len(file_data) + 5
                        temp_data = temp_data[0 : len(temp_data) - index]

                        total -= len(temp_data[18:])
                        start = False
                    elif len(seq_list) != 0 and seq_num == seq_list[-1] + 1:
                        seq_list.append(seq_num)
                        total -= len(temp_data[18:])
                    elif seq_num < seq_list[-1]:

                        transmitAck(seq_num, udp_socket)
                        # udp_socket.send(struct.pack("!BI", 0xFF, seq_num))
                        break
                    data += temp_data[18:]
                    transmitAck(seq_num, udp_socket)
                    # udp_socket.send(struct.pack("!BI", 0xFF, seq_num))

                    break
                else:
                    if seq_list[-1] != -1:
                        transmitAck(seq_list[-1], udp_socket)

            except socket.timeout:
                pass

        # end of sending one packet

    udp_socket.settimeout(0.2)
    while True:
        try:
            udp_socket.recv(2048)
            udp_socket.send(struct.pack("!BI", 0xFF, seq_list[-1]))
        except socket.timeout:
            break

    if len(file) != 0:
        output_to_file(data, file)
    else:
        print(data.decode())
    udp_socket.send(".".encode())
    udp_socket.send("QUIT".encode())


main()
