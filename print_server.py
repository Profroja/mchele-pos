#!/usr/bin/env python3
"""
Bluetooth Thermal Printer Server
Listens on localhost:5000 for print requests and sends ESC/POS commands to thermal printer via Bluetooth
"""
import bluetooth
import json
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# PT-210 printer MAC address
PRINTER_MAC = "86:67:7A:D5:8C:9C"
PRINTER_PORT = 1  # SPP port (usually 1 for thermal printers)


def send_to_printer(data):
    """Send raw bytes to Bluetooth thermal printer"""
    try:
        sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
        sock.connect((PRINTER_MAC, PRINTER_PORT))
        sock.send(data)
        sock.close()
        return True
    except Exception as e:
        print(f"Printer error: {e}")
        return False


def generate_barcode_label(barcode, product_name, weight, price):
    """Generate ESC/POS commands for barcode label - company name, product name, weight, then barcode"""
    ESC = b'\x1B'
    GS = b'\x1D'
    
    commands = []
    
    # Initialize printer
    commands.append(ESC + b'@')
    
    # Center alignment
    commands.append(ESC + b'a\x01')
    
    # Company name (double height for prominence)
    commands.append(ESC + b'!\x10')
    commands.append(b'Arusha Mchele Loft\n')
    
    # Reset to normal
    commands.append(ESC + b'!\x00')
    
    # Product name
    name = product_name or 'Rice'
    commands.append(name.encode('utf-8') + b'\n')
    
    # Weight
    weight_str = str(weight).replace('.0', '') if weight else ''
    commands.append(f'{weight_str}kg\n'.encode('utf-8'))
    
    # Small gap before barcode
    commands.append(b'\n')
    
    # Print CODE128 barcode
    barcode_bytes = barcode.encode('utf-8')
    commands.append(GS + b'k' + bytes([73, len(barcode_bytes)]) + barcode_bytes)
    
    # Feed and cut
    commands.append(b'\n\n')
    commands.append(GS + b'V\x42\x00')  # Full cut
    
    return b''.join(commands)


@app.route('/print', methods=['POST'])
def print_label():
    """Print barcode label endpoint"""
    try:
        data = request.json
        barcode = data.get('barcode', '')
        product_name = data.get('product_name', '')
        weight = data.get('weight', '')
        price = data.get('price', '')
        
        if not barcode:
            return jsonify({'success': False, 'message': 'Barcode is required'}), 400
        
        label_data = generate_barcode_label(barcode, product_name, weight, price)
        
        if send_to_printer(label_data):
            return jsonify({'success': True, 'message': f'Printed: {barcode}'})
        else:
            return jsonify({'success': False, 'message': 'Failed to send to printer. Check Bluetooth connection.'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/status', methods=['GET'])
def printer_status():
    """Check if printer is reachable"""
    try:
        # Try to discover the printer
        nearby = bluetooth.discover_devices(duration=2, lookup_names=True)
        printer_found = any(mac == PRINTER_MAC for mac, _ in nearby)
        
        return jsonify({
            'success': True,
            'printer_mac': PRINTER_MAC,
            'printer_found': printer_found,
            'nearby_devices': [{'mac': mac, 'name': name} for mac, name in nearby]
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


if __name__ == '__main__':
    print(f"Bluetooth Printer Server starting...")
    print(f"Printer MAC: {PRINTER_MAC}")
    print(f"Listening on http://localhost:5000")
    print(f"Endpoints: POST /print, GET /status")
    app.run(host='127.0.0.1', port=5000, debug=True)
