"use client";

import React, { useEffect, useState } from "react";
import { supabase, Job } from "@/lib/supabase";
import {
  Briefcase,
  MapPin,
  Clock,
  ExternalLink,
  Eye,
  CheckCircle2,
  Trash2,
  RefreshCw,
  Building2,
  Globe,
  Timer,
  CheckSquare,
  Square
} from "lucide-react";

const APP_PIN = process.env.NEXT_PUBLIC_APP_PIN || "1234";
const SYNC_INTERVAL_MINUTES = 60;

const cleanJobUrl = (url: string) => {
  if (!url) return "#";
  // Quita fragmentos #lc=... de Computrabajo que rompen el deep-link en la app mobile
  return url.includes("computrabajo.com") ? url.split("#")[0] : url;
};

const getBadgeClass = (source: string) => {
  const s = (source || "").toLowerCase();
  if (s === "computrabajo") return "bg-[#FFF3EB] text-[#D95B16] border border-[#FBD5BD]";
  if (s === "bumeran") return "bg-fuchsia-50 text-fuchsia-700 border border-fuchsia-200";
  if (s === "indeed") return "bg-blue-50 text-blue-700 border border-blue-200";
  if (s === "zonajobs") return "bg-rose-50 text-rose-700 border border-rose-200";
  return "bg-gray-100 text-gray-700 border border-gray-200";
};

function formatSyncInfo(lastSyncIso: string | null, nowMs: number): { agoText: string; nextText: string } {
  if (!lastSyncIso) {
    return { agoText: "Sin sincronizar aún", nextText: "Esperando primer ciclo" };
  }
  const syncMs = new Date(lastSyncIso).getTime();
  if (Number.isNaN(syncMs)) {
    return { agoText: "Sin datos", nextText: "—" };
  }
  const diffMin = Math.max(0, Math.floor((nowMs - syncMs) / 60000));

  let agoText = "";
  if (diffMin < 1) {
    agoText = "Actualizado recién";
  } else if (diffMin < 60) {
    agoText = `Actualizado hace ${diffMin} min`;
  } else {
    const hrs = Math.floor(diffMin / 60);
    const rem = diffMin % 60;
    agoText = rem > 0 ? `Actualizado hace ${hrs}h ${rem}m` : `Actualizado hace ${hrs}h`;
  }

  const remaining = SYNC_INTERVAL_MINUTES - diffMin;
  let nextText = "";
  if (remaining > 1) {
    nextText = `Próxima en ${remaining} min`;
  } else if (remaining === 1) {
    nextText = "Próxima en 1 min";
  } else {
    nextText = "Próxima actualización inminente";
  }

  return { agoText, nextText };
}

export default function Home() {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [pinInput, setPinInput] = useState<string>("");
  const [pinError, setPinError] = useState<boolean>(false);

  const [jobs, setJobs] = useState<Job[]>([]);
  const [lastSyncAt, setLastSyncAt] = useState<string | null>(null);
  const [nowMs, setNowMs] = useState<number>(Date.now());
  const [loading, setLoading] = useState<boolean>(true);
  const [activeTab, setActiveTab] = useState<"new" | "applied" | "discarded">("new");
  const [selectedSource, setSelectedSource] = useState<string>("all");
  const [previewJob, setPreviewJob] = useState<Job | null>(null);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [isDeleting, setIsDeleting] = useState<boolean>(false);

  // 1. Manejo de autenticación por PIN
  useEffect(() => {
    const savedAuth = localStorage.getItem("job_hunter_auth");
    if (savedAuth === "true") {
      setIsAuthenticated(true);
    }
  }, []);

  // Actualizar reloj local cada 30 segundos para refrescar el contador de minutos
  useEffect(() => {
    const timer = setInterval(() => setNowMs(Date.now()), 30000);
    return () => clearInterval(timer);
  }, []);

  const handlePinSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (pinInput === APP_PIN) {
      localStorage.setItem("job_hunter_auth", "true");
      setIsAuthenticated(true);
      setPinError(false);
    } else {
      setPinError(true);
      setPinInput("");
    }
  };

  // 2. Cargar ofertas y heartbeat de sincronización desde Supabase
  const fetchJobs = async () => {
    setLoading(true);
    try {
      const { data, error } = await supabase
        .from("jobs")
        .select("*")
        .order("created_at", { ascending: false });

      if (error) throw error;
      const allRows: Job[] = data || [];

      // Separar el registro de heartbeat del listado real de ofertas
      const heartbeatRow = allRows.find((r) => r.source === "__heartbeat__");
      const realJobs = allRows.filter((r) => r.source !== "__heartbeat__");

      setJobs(realJobs);

      if (heartbeatRow?.status_updated_at) {
        setLastSyncAt(heartbeatRow.status_updated_at);
      } else if (realJobs.length > 0) {
        setLastSyncAt(realJobs[0].created_at);
      } else {
        setLastSyncAt(null);
      }
      setNowMs(Date.now());
    } catch (err) {
      console.error("Error al cargar ofertas:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isAuthenticated) {
      fetchJobs();
    }
  }, [isAuthenticated]);

  // 3. Cambiar estado de una oferta (Postulado / Descartado)
  const updateJobStatus = async (jobId: string, newStatus: "applied" | "discarded") => {
    try {
      // Actualización optimista en UI
      setJobs((prev) =>
        prev.map((j) => (j.id === jobId ? { ...j, status: newStatus } : j))
      );

      if (previewJob?.id === jobId) {
        setPreviewJob(null);
      }

      const { error } = await supabase
        .from("jobs")
        .update({
          status: newStatus,
          status_updated_at: new Date().toISOString(),
        })
        .eq("id", jobId);

      if (error) throw error;
    } catch (err) {
      console.error("Error al actualizar estado:", err);
      fetchJobs(); // Revertir en caso de fallo
    }
  };

  // Limpiar selección al cambiar de pestaña o filtro de portal
  useEffect(() => {
    setSelectedIds([]);
  }, [activeTab, selectedSource]);

  // Filtrado de ofertas
  const filteredJobs = jobs.filter((job) => {
    const matchesTab = job.status === activeTab;
    const matchesSource =
      selectedSource === "all" ||
      (job.source || "").toLowerCase() === selectedSource.toLowerCase();
    return matchesTab && matchesSource;
  });

  const isHistoryTab = activeTab === "applied" || activeTab === "discarded";
  const allFilteredSelected =
    filteredJobs.length > 0 && filteredJobs.every((j) => selectedIds.includes(j.id));

  const toggleSelectJob = (jobId: string) => {
    setSelectedIds((prev) =>
      prev.includes(jobId) ? prev.filter((id) => id !== jobId) : [...prev, jobId]
    );
  };

  const toggleSelectAll = () => {
    if (allFilteredSelected) {
      setSelectedIds([]);
    } else {
      setSelectedIds(filteredJobs.map((j) => j.id));
    }
  };

  const deleteSelectedJobs = async () => {
    if (selectedIds.length === 0 || isDeleting) return;
    const count = selectedIds.length;
    const confirmed = window.confirm(
      `¿Eliminar ${count} ${count === 1 ? "oferta" : "ofertas"} del historial? Esta acción no se puede deshacer.`
    );
    if (!confirmed) return;

    const idsToDelete = [...selectedIds];
    setIsDeleting(true);
    try {
      // Actualización optimista en UI
      setJobs((prev) => prev.filter((j) => !idsToDelete.includes(j.id)));
      setSelectedIds([]);
      if (previewJob && idsToDelete.includes(previewJob.id)) {
        setPreviewJob(null);
      }

      const { error } = await supabase
        .from("jobs")
        .delete()
        .in("id", idsToDelete)
        .neq("source", "__heartbeat__");

      if (error) throw error;
    } catch (err) {
      console.error("Error al eliminar ofertas:", err);
      fetchJobs(); // Revertir en caso de fallo
    } finally {
      setIsDeleting(false);
    }
  };

  const countNew = jobs.filter((j) => j.status === "new").length;
  const countApplied = jobs.filter((j) => j.status === "applied").length;
  const countDiscarded = jobs.filter((j) => j.status === "discarded").length;
  const syncInfo = formatSyncInfo(lastSyncAt, nowMs);

  // Pantalla de bloqueo estilo Computrabajo
  if (!isAuthenticated) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#F3F5F8] p-4">
        <div className="w-full max-w-sm overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-lg">
          <div className="bg-[#0D3878] px-6 py-7 text-center">
            <div className="mx-auto flex h-16 w-16 items-center justify-center overflow-hidden rounded-2xl bg-white p-1 shadow-md">
              <img
                src="/logo.svg"
                alt="Agarra la pala"
                className="h-full w-full object-contain"
              />
            </div>
            <h1 className="mt-4 text-2xl font-extrabold tracking-tight text-white">
              Agarra la <span className="text-emerald-400">pala</span>
            </h1>
            <p className="mt-1 text-xs text-blue-100">Ingresa tu PIN de acceso personal</p>
          </div>

          <form onSubmit={handlePinSubmit} className="p-6 space-y-4">
            <div>
              <input
                type="password"
                inputMode="numeric"
                pattern="[0-9]*"
                maxLength={6}
                value={pinInput}
                onChange={(e) => setPinInput(e.target.value)}
                placeholder="Ingresar PIN"
                className="w-full rounded-xl border border-gray-300 bg-[#F8FAFC] px-4 py-3 text-center text-2xl tracking-widest text-[#0D3878] focus:border-[#0D3878] focus:bg-white focus:outline-none focus:ring-2 focus:ring-[#0D3878]/20"
                autoFocus
              />
              {pinError && (
                <p className="mt-2 text-center text-xs text-rose-600 font-medium">
                  PIN incorrecto. Inténtalo de nuevo.
                </p>
              )}
            </div>
            <button
              type="submit"
              className="w-full rounded-xl bg-emerald-600 py-3 font-semibold text-white shadow-sm transition hover:bg-emerald-700 active:scale-[0.98]"
            >
              Ingresar
            </button>
          </form>
        </div>
      </main>
    );
  }

  return (
    <main className="mx-auto min-h-screen max-w-md bg-[#F3F5F8] pb-24 text-[#1F2937]">
      {/* HEADER ESTILO COMPUTRABAJO */}
      <header className="sticky top-0 z-30 bg-[#0D3878] px-4 pt-3.5 pb-3 text-white shadow-md">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="flex h-10 w-10 items-center justify-center overflow-hidden rounded-xl bg-white p-0.5 shadow-sm">
              <img
                src="/logo.svg"
                alt="Agarra la pala"
                className="h-full w-full object-contain"
              />
            </div>
            <div>
              <h1 className="text-lg font-extrabold leading-none tracking-tight text-white">
                Agarra la <span className="text-emerald-400">pala</span>
              </h1>
              <span className="text-[11px] text-blue-200 font-medium">
                Ofertas recientes (máx. 24h)
              </span>
            </div>
          </div>
          <button
            onClick={fetchJobs}
            disabled={loading}
            title="Actualizar ahora"
            className="flex h-9 w-9 items-center justify-center rounded-xl bg-white/15 text-white transition hover:bg-white/25 active:scale-95 disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>

        {/* BARRA DE ESTADO DE SINCRONIZACIÓN DE BASE DE DATOS */}
        <div className="mt-3 flex items-center justify-between rounded-lg bg-[#082654]/80 px-3 py-1.5 text-[11px] text-blue-100 border border-white/10">
          <span className="flex items-center gap-1.5 font-medium">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            {syncInfo.agoText}
          </span>
          <span className="flex items-center gap-1 font-semibold text-[#FFB27D]">
            <Timer className="h-3.5 w-3.5" />
            {syncInfo.nextText}
          </span>
        </div>

        {/* SELECTOR DE FUENTE (Portales) */}
        <div className="mt-3 flex gap-1.5 overflow-x-auto pb-0.5 text-xs scrollbar-none">
          {["all", "computrabajo", "bumeran", "indeed", "zonajobs"].map((src) => (
            <button
              key={src}
              onClick={() => setSelectedSource(src)}
              className={`whitespace-nowrap rounded-full px-3.5 py-1.5 font-semibold capitalize transition ${
                selectedSource === src
                  ? "bg-white text-[#0D3878] shadow-sm"
                  : "bg-white/10 text-blue-100 hover:bg-white/20"
              }`}
            >
              {src === "all" ? "Todas las fuentes" : src}
            </button>
          ))}
        </div>
      </header>

      {/* PESTAÑAS DE ESTADO (Nuevas, Postuladas, Descartadas) */}
      <div className="flex border-b border-gray-200 bg-white px-2 text-xs font-bold shadow-sm">
        <button
          onClick={() => setActiveTab("new")}
          className={`flex-1 border-b-[3px] py-3 text-center transition ${
            activeTab === "new"
              ? "border-[#F36F21] text-[#0D3878]"
              : "border-transparent text-gray-500 hover:text-gray-700"
          }`}
        >
          Nuevas{" "}
          <span
            className={`ml-1 rounded-full px-1.5 py-0.5 text-[10px] ${
              activeTab === "new"
                ? "bg-[#FFF3EB] text-[#D95B16]"
                : "bg-gray-100 text-gray-500"
            }`}
          >
            {countNew}
          </span>
        </button>
        <button
          onClick={() => setActiveTab("applied")}
          className={`flex-1 border-b-[3px] py-3 text-center transition ${
            activeTab === "applied"
              ? "border-[#F36F21] text-[#0D3878]"
              : "border-transparent text-gray-500 hover:text-gray-700"
          }`}
        >
          Postuladas{" "}
          <span
            className={`ml-1 rounded-full px-1.5 py-0.5 text-[10px] ${
              activeTab === "applied"
                ? "bg-emerald-50 text-emerald-700"
                : "bg-gray-100 text-gray-500"
            }`}
          >
            {countApplied}
          </span>
        </button>
        <button
          onClick={() => setActiveTab("discarded")}
          className={`flex-1 border-b-[3px] py-3 text-center transition ${
            activeTab === "discarded"
              ? "border-[#F36F21] text-[#0D3878]"
              : "border-transparent text-gray-500 hover:text-gray-700"
          }`}
        >
          Descartadas{" "}
          <span
            className={`ml-1 rounded-full px-1.5 py-0.5 text-[10px] ${
              activeTab === "discarded"
                ? "bg-gray-200 text-gray-700"
                : "bg-gray-100 text-gray-500"
            }`}
          >
            {countDiscarded}
          </span>
        </button>
      </div>

      {/* LISTADO DE OFERTAS */}
      <section className="p-3.5 space-y-3">
        {/* BARRA DE LIMPIEZA (solo en Postuladas y Descartadas) */}
        {!loading && isHistoryTab && filteredJobs.length > 0 && (
          <div className="flex items-center justify-between gap-2 rounded-xl border border-gray-200 bg-white px-3 py-2.5 shadow-sm">
            <button
              type="button"
              onClick={toggleSelectAll}
              className="flex items-center gap-1.5 rounded-lg border border-[#0D3878]/25 bg-[#F0F5FC] px-3 py-1.5 text-xs font-bold text-[#0D3878] transition hover:bg-[#E1ECFA] active:scale-95"
            >
              {allFilteredSelected ? (
                <CheckSquare className="h-3.5 w-3.5 text-[#F36F21]" />
              ) : (
                <Square className="h-3.5 w-3.5" />
              )}
              {allFilteredSelected ? "Quitar selección" : "Seleccionar todo"}
            </button>

            <button
              type="button"
              onClick={deleteSelectedJobs}
              disabled={selectedIds.length === 0 || isDeleting}
              className="flex items-center gap-1.5 rounded-lg bg-rose-600 px-3 py-1.5 text-xs font-bold text-white shadow-sm transition hover:bg-rose-700 active:scale-95 disabled:cursor-not-allowed disabled:bg-gray-200 disabled:text-gray-400 disabled:shadow-none"
            >
              <Trash2 className="h-3.5 w-3.5" />
              {isDeleting ? "Borrando..." : `Borrar (${selectedIds.length})`}
            </button>
          </div>
        )}

        {loading ? (
          <div className="flex flex-col items-center justify-center py-16 text-gray-500">
            <RefreshCw className="h-6 w-6 animate-spin text-[#0D3878]" />
            <p className="mt-3 text-xs font-medium">Buscando ofertas recientes...</p>
          </div>
        ) : filteredJobs.length === 0 ? (
          <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-gray-300 bg-white py-14 px-6 text-center text-gray-500">
            <Briefcase className="h-9 w-9 text-gray-300 mb-2" />
            <p className="text-sm font-bold text-[#0D3878]">No hay ofertas en esta sección</p>
            <p className="text-xs text-gray-500 mt-1 max-w-[260px]">
              {activeTab === "new"
                ? "El bot buscará nuevas vacantes automáticamente en el próximo ciclo."
                : "Las ofertas aquí se limpian automáticamente tras 24 horas."}
            </p>
          </div>
        ) : (
          filteredJobs.map((job) => {
            const isSelected = selectedIds.includes(job.id);
            return (
            <article
              key={job.id}
              className={`rounded-xl border p-4 shadow-sm transition hover:shadow-md ${
                isSelected
                  ? "border-[#0D3878] bg-[#F8FBFF] ring-1 ring-[#0D3878]/20"
                  : "border-gray-200 bg-white hover:border-[#0D3878]/40"
              }`}
            >
              {/* CABECERA DE LA TARJETA */}
              <div className="flex items-center justify-between text-[11px] mb-2">
                <div className="flex items-center gap-2">
                  {isHistoryTab && (
                    <button
                      type="button"
                      onClick={() => toggleSelectJob(job.id)}
                      aria-label={isSelected ? "Deseleccionar oferta" : "Seleccionar oferta"}
                      className="flex items-center justify-center text-[#0D3878] hover:text-[#F36F21] transition active:scale-90"
                    >
                      {isSelected ? (
                        <CheckSquare className="h-4 w-4 text-[#F36F21]" />
                      ) : (
                        <Square className="h-4 w-4 text-gray-400" />
                      )}
                    </button>
                  )}
                  <span
                    className={`flex items-center gap-1 rounded-md px-2 py-0.5 font-bold uppercase tracking-wider ${getBadgeClass(
                      job.source
                    )}`}
                  >
                    <Globe className="h-3 w-3" />
                    {job.source}
                  </span>
                </div>
                <span className="flex items-center gap-1 font-medium text-[#5C6873]">
                  <Clock className="h-3 w-3 text-[#0D3878]/70" />
                  {job.published_time_text}
                </span>
              </div>

              {/* TÍTULO Y EMPRESA */}
              <h2 className="text-[15px] font-bold text-[#0D3878] line-clamp-2 leading-snug">
                {job.title}
              </h2>
              <div className="mt-2 flex flex-col gap-1 text-xs text-[#5C6873]">
                <span className="flex items-center gap-1.5 font-semibold text-[#1F2937]">
                  <Building2 className="h-3.5 w-3.5 text-gray-400 flex-shrink-0" />
                  {job.company}
                </span>
                <span className="flex items-center gap-1.5">
                  <MapPin className="h-3.5 w-3.5 text-gray-400 flex-shrink-0" />
                  {job.location}
                </span>
              </div>

              {/* ACCIONES DE LA TARJETA */}
              <div className="mt-4 flex items-center gap-2 pt-3 border-t border-gray-100">
                {/* Botón Vista Previa */}
                <button
                  onClick={() => setPreviewJob(job)}
                  className="flex flex-1 items-center justify-center gap-1.5 rounded-lg border border-[#0D3878]/25 bg-[#F0F5FC] py-2.5 text-xs font-bold text-[#0D3878] transition hover:bg-[#E1ECFA] active:scale-95"
                >
                  <Eye className="h-3.5 w-3.5" />
                  Vista Previa
                </button>

                {/* Botón Postularme */}
                {job.status === "new" && (
                  <>
                    <a
                      href={cleanJobUrl(job.url)}
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={() => updateJobStatus(job.id, "applied")}
                      className="flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-emerald-600 py-2.5 text-xs font-bold text-white shadow-sm transition hover:bg-emerald-700 active:scale-95"
                    >
                      <ExternalLink className="h-3.5 w-3.5" />
                      Postularme
                    </a>
                    <button
                      onClick={() => updateJobStatus(job.id, "discarded")}
                      title="Descartar"
                      className="flex h-9 w-9 items-center justify-center rounded-lg border border-gray-200 bg-gray-50 text-gray-400 hover:border-rose-200 hover:bg-rose-50 hover:text-rose-600 transition active:scale-95"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </>
                )}

                {job.status === "applied" && (
                  <a
                    href={cleanJobUrl(job.url)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex flex-1 items-center justify-center gap-1.5 rounded-lg border border-emerald-200 bg-emerald-50 py-2.5 text-xs font-bold text-emerald-700"
                  >
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    Ver aviso oficial
                  </a>
                )}

                {job.status === "discarded" && (
                  <button
                    onClick={() => updateJobStatus(job.id, "applied")}
                    className="flex flex-1 items-center justify-center gap-1.5 rounded-lg border border-gray-300 bg-white py-2.5 text-xs font-semibold text-gray-700 hover:bg-gray-50"
                  >
                    Restaurar a Postuladas
                  </button>
                )}
              </div>
            </article>
            );
          })
        )}
      </section>

      {/* MODAL / DRAWER DE VISTA PREVIA COMPLETA */}
      {previewJob && (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-[#0D3878]/40 backdrop-blur-[2px] p-0 sm:items-center sm:p-4">
          <div className="w-full max-w-lg rounded-t-2xl sm:rounded-2xl border border-gray-200 bg-white p-5 shadow-2xl max-h-[85vh] flex flex-col">
            {/* Header del Modal */}
            <div className="flex items-start justify-between border-b border-gray-200 pb-3">
              <div className="pr-3">
                <span
                  className={`inline-block rounded px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${getBadgeClass(
                    previewJob.source
                  )}`}
                >
                  {previewJob.source}
                </span>
                <h2 className="mt-1.5 text-base font-bold text-[#0D3878] leading-snug">
                  {previewJob.title}
                </h2>
                <p className="text-xs text-[#5C6873] mt-0.5 font-medium">
                  {previewJob.company} • {previewJob.location}
                </p>
              </div>
              <button
                onClick={() => setPreviewJob(null)}
                className="h-8 w-8 flex-shrink-0 rounded-full bg-gray-100 text-gray-500 hover:bg-gray-200 hover:text-gray-800 flex items-center justify-center font-bold"
              >
                ✕
              </button>
            </div>

            {/* Contenido / Requisitos */}
            <div className="my-4 overflow-y-auto pr-1 text-xs text-[#374151] leading-relaxed space-y-3">
              <div className="rounded-xl bg-[#F8FAFC] p-4 border border-gray-200">
                <h3 className="font-bold text-[#0D3878] mb-2 text-xs uppercase tracking-wide">
                  Resumen del aviso
                </h3>
                <p className="whitespace-pre-wrap">
                  {previewJob.full_description || "Sin descripción disponible."}
                </p>
              </div>
              <div className="flex items-center gap-2 text-[#5C6873] text-[11px] font-medium">
                <Clock className="h-3.5 w-3.5 text-[#0D3878]" />
                <span>Publicado: {previewJob.published_time_text}</span>
              </div>
            </div>

            {/* Acciones del Modal */}
            <div className="pt-3 border-t border-gray-200 flex gap-2">
              <a
                href={cleanJobUrl(previewJob.url)}
                target="_blank"
                rel="noopener noreferrer"
                onClick={() => updateJobStatus(previewJob.id, "applied")}
                className="flex-1 rounded-xl bg-emerald-600 py-3 text-center text-xs font-bold text-white shadow-sm hover:bg-emerald-700 transition capitalize"
              >
                Ir a Postularme en {previewJob.source}
              </a>
              {previewJob.status === "new" && (
                <button
                  onClick={() => updateJobStatus(previewJob.id, "discarded")}
                  className="rounded-xl border border-gray-300 bg-white px-4 text-xs font-bold text-gray-600 hover:bg-gray-50 transition"
                >
                  Descartar
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
