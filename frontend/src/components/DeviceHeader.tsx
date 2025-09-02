'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { FiMonitor, FiWifi, FiShield, FiActivity } from 'react-icons/fi';
import { Badge } from '@/components/ui/Badge';

interface DeviceHeaderProps {
  selectedDevice: string;
  onDeviceChange: (device: string) => void;
}

const devices = [
  { id: 'DA', name: 'Device Alpha', type: 'Medical Scanner', status: 'online' },
  { id: 'DB', name: 'Device Beta', type: 'Lab Analyzer', status: 'online' },
  { id: 'DC', name: 'Device Charlie', type: 'Imaging Unit', status: 'maintenance' },
  { id: 'DD', name: 'Device Delta', type: 'Diagnostic Tool', status: 'online' },
  { id: 'DE', name: 'Device Echo', type: 'Patient Monitor', status: 'offline' },
  { id: 'DCX', name: 'Medical Device X', type: 'Research Unit', status: 'online' }
];

export default function DeviceHeader({ selectedDevice, onDeviceChange }: DeviceHeaderProps) {
  const currentDevice = devices.find(d => d.id === selectedDevice);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'online': return 'bg-green-100 text-green-800 border-green-200';
      case 'offline': return 'bg-red-100 text-red-800 border-red-200';
      case 'maintenance': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'online': return <FiWifi className="w-3 h-3" />;
      case 'offline': return <FiShield className="w-3 h-3" />;
      case 'maintenance': return <FiActivity className="w-3 h-3" />;
      default: return <FiMonitor className="w-3 h-3" />;
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-gradient-to-r from-blue-50 to-indigo-50 border-b border-blue-100"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-blue-100 rounded-lg">
                <FiMonitor className="h-5 w-5 text-blue-600" />
              </div>
              <div>
                <label htmlFor="device-select" className="text-sm font-medium text-gray-700 block">
                  Select Device:
                </label>
                <select
                  id="device-select"
                  value={selectedDevice}
                  onChange={(e) => onDeviceChange(e.target.value)}
                  className="block w-64 px-3 py-2 mt-1 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 sm:text-sm bg-white"
                >
                  <option value="">Choose a device...</option>
                  {devices.map((device) => (
                    <option key={device.id} value={device.id}>
                      {device.name} ({device.id}) - {device.type}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {currentDevice && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="flex items-center space-x-4"
            >
              <div className="text-right">
                <div className="text-lg font-semibold text-gray-900">
                  {currentDevice.name}
                </div>
                <div className="text-sm text-gray-600">
                  {currentDevice.type}
                </div>
              </div>
              <Badge
                variant="outline"
                className={`flex items-center space-x-1 ${getStatusColor(currentDevice.status)}`}
              >
                {getStatusIcon(currentDevice.status)}
                <span className="capitalize">{currentDevice.status}</span>
              </Badge>
            </motion.div>
          )}
        </div>
      </div>
    </motion.div>
  );
}
