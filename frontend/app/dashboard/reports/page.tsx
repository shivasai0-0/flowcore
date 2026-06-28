'use client';

import React, { useEffect, useState, useRef } from 'react';
import { useWorkflowStore } from '@/stores/workflowStore';
import { api } from '@/services/api';
import { 
  FileText, 
  Send, 
  CheckCircle, 
  XCircle, 
  Loader2, 
  Clock, 
  Download,
  FileBarChart
} from 'lucide-react';

type ToastType = { message: string; type: 'success' | 'error' };

const reportOptionsMap: Record<string, { label: string; value: string }[]> = {
  restaurant: [
    { label: 'Daily Orders Report (Restaurant/E-comm)', value: 'Daily Orders Report' }
  ],
  ecommerce: [
    { label: 'Daily Orders Report (Restaurant/E-comm)', value: 'Daily Orders Report' }
  ],
  hospital: [
    { label: 'Doctor Appointment Schedule (Hospital/Clinic)', value: 'Doctor Appointment Schedule' }
  ],
  clinic: [
    { label: 'Doctor Appointment Schedule (Hospital/Clinic)', value: 'Doctor Appointment Schedule' }
  ],
  salon: [
    { label: "Today's Salon Bookings (Salon/Beauty)", value: "Today's Appointments" }
  ],
  beauty: [
    { label: "Today's Salon Bookings (Salon/Beauty)", value: "Today's Appointments" }
  ],
  gym: [
    { label: 'Member Check-ins (Gym/Athletics)', value: 'Member Attendance' }
  ],
  athletics: [
    { label: 'Member Check-ins (Gym/Athletics)', value: 'Member Attendance' }
  ]
};

export default function ReportsCenterPage() {
  const { businessId, whatsappNumber } = useWorkflowStore();
  const [reports, setReports] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [businessType, setBusinessType] = useState<string>('restaurant');
  const [reportType, setReportType] = useState('Daily Orders Report');
  const [recipient, setRecipient] = useState(whatsappNumber || '');
  
  const [isGenerating, setIsGenerating] = useState(false);
  const [isDelivering, setIsDelivering] = useState(false);
  const [selectedReport, setSelectedReport] = useState<any | null>(null);

  const [toast, setToast] = useState<ToastType | null>(null);
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const showToast = (message: string, type: 'success' | 'error') => {
    if (toastTimer.current) clearTimeout(toastTimer.current);
    setToast({ message, type });
    toastTimer.current = setTimeout(() => setToast(null), 4000);
  };

  const fetchReports = async () => {
    if (!businessId) return;
    setLoading(true);
    try {
      const bizRes = await api.getBusiness(businessId);
      if (bizRes.success && bizRes.data) {
        const type = bizRes.data.business_type || 'restaurant';
        setBusinessType(type);
        
        // Auto-select correct default reportType based on business type
        const typeKey = type.toLowerCase();
        if (reportOptionsMap[typeKey] && reportOptionsMap[typeKey].length > 0) {
          setReportType(reportOptionsMap[typeKey][0].value);
        } else {
          setReportType('Daily Summary Report');
        }
      }
      const res = await api.listReportsHistory(businessId);
      if (res.success && res.data) {
        setReports(res.data);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setSelectedReport(null);
    fetchReports();
  }, [businessId]);

  const handleGenerate = async () => {
    if (!businessId) return;
    setIsGenerating(true);
    try {
      const res = await api.generateReport(businessId, reportType);
      if (res.success && res.data) {
        showToast(`📊 Report successfully compiled!`, 'success');
        setSelectedReport(res.data);
        await fetchReports();
      } else {
        showToast(`❌ Generation failed: ${res.error?.message || 'Unknown error'}`, 'error');
      }
    } catch (err: any) {
      showToast(`❌ ${err.message}`, 'error');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleSendWhatsapp = async () => {
    if (!selectedReport || !recipient.trim()) return;
    setIsDelivering(true);
    try {
      const res = await api.sendReportWhatsapp(recipient, selectedReport.content);
      if (res.success) {
        showToast(`📱 Report successfully sent to ${recipient} via WhatsApp!`, 'success');
      } else {
        showToast(`❌ Send failed: ${res.error?.message || 'Unknown error'}`, 'error');
      }
    } catch (err: any) {
      showToast(`❌ ${err.message}`, 'error');
    } finally {
      setIsDelivering(false);
    }
  };

  const getReportOptions = () => {
    const typeKey = businessType.toLowerCase();
    if (reportOptionsMap[typeKey]) {
      return reportOptionsMap[typeKey];
    }
    return [
      { label: 'Daily Summary Report', value: 'Daily Summary Report' }
    ];
  };

  const displayReports = reports.filter(r => {
    const options = getReportOptions();
    return options.some(opt => opt.value === r.report_type);
  });

  return (
    <div className="flex-1 p-8 flex flex-col gap-6 bg-slate-50/50 relative">
      {/* Toast */}
      {toast && (
        <div className={`fixed top-5 right-5 z-50 px-4 py-3 rounded-xl shadow-lg text-xs font-bold flex items-center gap-2 transition-all ${
          toast.type === 'success'
            ? 'bg-emerald-50 border border-emerald-200 text-emerald-800'
            : 'bg-rose-50 border border-rose-200 text-rose-800'
        }`}>
          {toast.type === 'success' ? <CheckCircle className="w-4 h-4 text-emerald-600" /> : <XCircle className="w-4 h-4 text-rose-600" />}
          {toast.message}
        </div>
      )}

      {/* Header */}
      <div>
        <h2 className="font-outfit font-bold text-xl text-slate-900">Reports Center</h2>
        <p className="text-xs text-slate-500 mt-1">Compile analytical schedules or summaries and dispatch them to WhatsApp notification endpoints.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Options Card */}
        <div className="lg:col-span-1 flex flex-col gap-6">
          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm flex flex-col gap-4">
            <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2 uppercase tracking-wider border-b border-slate-100 pb-3">
              <FileBarChart className="w-4 h-4 text-emerald-600" /> Generate Report
            </h3>

            <div className="flex flex-col gap-3 text-xs">
              <div className="flex flex-col gap-1">
                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Report Schema</label>
                <select
                  value={reportType}
                  onChange={e => setReportType(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors cursor-pointer font-medium"
                >
                  {getReportOptions().map((opt) => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </div>

              <button
                onClick={handleGenerate}
                disabled={isGenerating}
                className="w-full flex items-center justify-center gap-1.5 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs shadow-md transition-all cursor-pointer disabled:opacity-50 mt-2"
              >
                {isGenerating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <FileText className="w-3.5 h-3.5" />}
                Generate Report
              </button>
            </div>
          </div>

          {selectedReport && (
            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm flex flex-col gap-4">
              <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2 uppercase tracking-wider border-b border-slate-100 pb-3">
                <Send className="w-4 h-4 text-emerald-600" /> WhatsApp Dispatcher
              </h3>
              
              <div className="flex flex-col gap-3 text-xs">
                <div className="flex flex-col gap-1">
                  <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Recipient Phone Number</label>
                  <input
                    type="text"
                    value={recipient}
                    onChange={e => setRecipient(e.target.value)}
                    placeholder="e.g. +15550199"
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors"
                  />
                </div>

                <button
                  onClick={handleSendWhatsapp}
                  disabled={isDelivering || !recipient.trim()}
                  className="w-full flex items-center justify-center gap-1.5 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs shadow-md transition-all cursor-pointer disabled:opacity-50 mt-1"
                >
                  {isDelivering ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                  Deliver via WhatsApp
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Right Details Panel */}
        <div className="lg:col-span-2 flex flex-col gap-6">
          {selectedReport ? (
            <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col gap-4">
              <div className="flex justify-between items-start border-b border-slate-100 pb-3">
                <div>
                  <h3 className="font-extrabold text-base text-slate-800">{selectedReport.report_type}</h3>
                  <span className="text-[10px] text-slate-400 font-mono">Report ID: {selectedReport.id}</span>
                </div>
                <button className="flex items-center gap-1 text-[10px] font-bold text-slate-500 hover:text-emerald-600 transition-colors">
                  <Download className="w-3.5 h-3.5" /> Export PDF
                </button>
              </div>

              <div className="p-4 bg-slate-900 text-slate-200 rounded-xl font-mono text-xs whitespace-pre-wrap leading-relaxed shadow-inner">
                {selectedReport.content}
              </div>
            </div>
          ) : (
            <div className="bg-white border border-slate-200 rounded-xl p-8 text-center text-xs text-slate-400 font-semibold flex flex-col items-center justify-center gap-2 h-64 shadow-sm">
              <FileText className="w-8 h-8 text-slate-300" />
              Configure a report format and click Generate to see compiling output.
            </div>
          )}

          {/* History */}
          <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col gap-4">
            <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider">Reports Log History</h3>
            <div className="flex flex-col gap-2 max-h-48 overflow-y-auto">
              {displayReports.length > 0 ? (
                displayReports.map(r => (
                  <div 
                    key={r.id} 
                    onClick={() => setSelectedReport(r)}
                    className="flex justify-between items-center p-3 rounded-lg border border-slate-100 hover:border-slate-350 cursor-pointer bg-slate-50/20 text-xs transition-colors"
                  >
                    <div className="flex flex-col gap-0.5">
                      <span className="font-bold text-slate-800">{r.report_type}</span>
                      <span className="text-[10px] text-slate-400 font-mono">ID: {r.id}</span>
                    </div>
                    <span className="text-[10px] text-slate-400 font-semibold font-mono">
                      {new Date(r.generated_at).toLocaleDateString()}
                    </span>
                  </div>
                ))
              ) : (
                <div className="p-4 text-center text-xs text-slate-400 font-semibold border border-dashed border-slate-200 rounded-lg bg-slate-50/50">
                  No reports logged for this business type.
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
