'use client';

import { useState, useEffect } from 'react';

interface Device {
  id: string;
  name: string;
  description: string;
  is_active: boolean;
}

interface DeviceSelectorProps {
  selectedDevice: string;
  onDeviceSelect: (deviceId: string) => void;
}

export default function DeviceSelector({ selectedDevice, onDeviceSelect }: DeviceSelectorProps) {
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchDevices();
  }, []);

  const fetchDevices = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/devices/');
      if (!response.ok) {
        throw new Error('Failed to fetch devices');
      }
      const data = await response.json();
      setDevices(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center space-x-2">
        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
        <span className="text-sm text-gray-600">Loading devices...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-red-600 text-sm">
        Error loading devices: {error}
      </div>
    );
  }

  return (
    <div className="flex items-center space-x-4">
      <label htmlFor="device-select" className="text-sm font-medium text-gray-700">
        Select Device:
      </label>
      <select
        id="device-select"
        value={selectedDevice}
        onChange={(e) => onDeviceSelect(e.target.value)}
        className="block w-48 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
      >
        <option value="">Choose a device...</option>
        {devices
          .filter(device => device.is_active)
          .map((device) => (
            <option key={device.id} value={device.id}>
              {device.name} ({device.id})
            </option>
          ))
        }
      </select>
      
      {selectedDevice && (
        <div className="flex items-center space-x-2">
          <div className="w-2 h-2 bg-green-500 rounded-full"></div>
          <span className="text-sm text-gray-600">
            {devices.find(d => d.id === selectedDevice)?.name}
          </span>
        </div>
      )}
    </div>
  );
}
