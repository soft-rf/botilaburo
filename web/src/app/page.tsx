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
  Lock, 
  Building2, 
  Globe 
} from "lucide-react";

const APP_PIN = process.env.NEXT_PUBLIC_APP_PIN || "1234";

export default function Home() {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [pinInput, setPinInput] = useState<string>("");
  const [pinError, setPinError] = useState<boolean>(false);

  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [activeTab, setActiveTab] = useState<"new" | "applied" | "discarded">("new");
  const [selectedSource, setSelectedSource] = useState<string>("all");
  const [previewJob, setPreviewJob] = useState<Job | null>(null);

  // 1. Manejo de autenticación por PIN
  useEffect(() => {
    const savedAuth = localStorage.getItem("job_hunter_auth");
    if (savedAuth === "true") {
      setIsAuthenticated(true);
    }
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

  // 2. Cargar ofertas desde Supabase
  const fetchJobs = async () => {
    setLoading(true);
    try {
      const { data, error } = await supabase
        .from("jobs")
        .select("*")
        .order("created_at", { ascending: false });

      if (error) throw error;
      setJobs(data || []);
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

  // Filtrado de ofertas
  const filteredJobs = jobs.filter((job) => {
    const matchesTab = job.status === activeTab;
    const matchesSource =
      selectedSource === "all" ||
      job.source.toLowerCase() === selectedSource.toLowerCase();
    return matchesTab && matchesSource;
  });

  const countNew = jobs.filter((j) => j.status === "new").length;
  const countApplied = jobs.filter((j) => j.status === "applied").length;
  const countDiscarded = jobs.filter((j) => j.status === "discarded").length;

  // Pantalla de bloqueo si no tiene el PIN
  if (!isAuthenticated) {
    return (
      <main className="flex min-h-screen items-center justify-center p-4">
        <div className="w-full max-w-sm rounded-2xl border border-slate-800 bg-slate-900/80 p-8 shadow-2xl backdrop-blur-xl">
          <div className="flex flex-col items-center text-center">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-500/10 text-emerald-400">
              <Lock className="h-7 w-7" />
            </div>
            <h1 className="mt-4 text-2xl font-bold tracking-tight text-white">Job Hunter Bot</h1>
            <p className="mt-1 text-sm text-slate-400">Ingresa tu PIN de acceso personal</p>
          </div>

          <form onSubmit={handlePinSubmit} className="mt-6 space-y-4">
            <div>
              <input
                type="password"
                inputMode="numeric"
                pattern="[0-9]*"
                maxLength={6}
                value={pinInput}
                onChange={(e) => setPinInput(e.target.value)}
                placeholder="Ingresar PIN"
                className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-center text-2xl tracking-widest text-white focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
                autoFocus
              />
              {pinError && (
                <p className="mt-2 text-center text-xs text-rose-400 font-medium">
                  PIN incorrecto. Inténtalo de nuevo.
                </p>
              )}
            </div>
            <button
              type="submit"
              className="w-full rounded-xl bg-emerald-500 py-3 font-semibold text-slate-950 transition hover:bg-emerald-400 active:scale-[0.98]"
            >
              Desbloquear
            </button>
          </form>
        </div>
      </main>
    );
  }

  return (
    <main className="mx-auto min-h-screen max-w-md pb-24 text-slate-100">
      {/* HEADER SUPERIOR */}
      <header className="sticky top-0 z-30 border-b border-slate-800/80 bg-slate-950/80 px-4 py-3 backdrop-blur-md">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-400">
              <Briefcase className="h-4 w-4" />
            </div>
            <div>
              <h1 className="text-base font-bold leading-none text-white">Job Hunter</h1>
              <div className="flex items-center gap-1.5 mt-1">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                <span className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">En tiempo real</span>
              </div>
            </div>
          </div>
          <button
            onClick={fetchJobs}
            disabled={loading}
            className="flex h-8 w-8 items-center justify-center rounded-lg border border-slate-800 bg-slate-900 text-slate-300 hover:text-white active:scale-95 disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin text-emerald-400" : ""}`} />
          </button>
        </div>

        {/* SELECTOR DE FUENTE (Portales) */}
        <div className="mt-3 flex gap-1.5 overflow-x-auto pb-1 text-xs scrollbar-none">
          {["all", "computrabajo", "bumeran", "indeed"].map((src) => (
            <button
              key={src}
              onClick={() => setSelectedSource(src)}
              className={`rounded-full px-3 py-1 font-medium capitalize transition ${
                selectedSource === src
                  ? "bg-slate-200 text-slate-950"
                  : "bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800"
              }`}
            >
              {src === "all" ? "Todas las fuentes" : src}
            </button>
          ))}
        </div>
      </header>

      {/* PESTAÑAS DE ESTADO (Nuevas, Postuladas, Descartadas) */}
      <div className="flex border-b border-slate-800/80 bg-slate-900/40 px-2 text-xs font-semibold">
        <button
          onClick={() => setActiveTab("new")}
          className={`flex-1 border-b-2 py-3 text-center transition ${
            activeTab === "new"
              ? "border-emerald-500 text-emerald-400"
              : "border-transparent text-slate-400 hover:text-slate-300"
          }`}
        >
          🔥 Nuevas ({countNew})
        </button>
        <button
          onClick={() => setActiveTab("applied")}
          className={`flex-1 border-b-2 py-3 text-center transition ${
            activeTab === "applied"
              ? "border-emerald-500 text-emerald-400"
              : "border-transparent text-slate-400 hover:text-slate-300"
          }`}
        >
          ✅ Postuladas ({countApplied})
        </button>
        <button
          onClick={() => setActiveTab("discarded")}
          className={`flex-1 border-b-2 py-3 text-center transition ${
            activeTab === "discarded"
              ? "border-emerald-500 text-emerald-400"
              : "border-transparent text-slate-400 hover:text-slate-300"
          }`}
        >
          🗑️ Descartadas ({countDiscarded})
        </button>
      </div>

      {/* LISTADO DE OFERTAS */}
      <section className="p-4 space-y-3">
        {loading ? (
          <div className="flex flex-col items-center justify-center py-16 text-slate-500">
            <RefreshCw className="h-6 w-6 animate-spin text-emerald-500" />
            <p className="mt-3 text-xs">Cargando oportunidades...</p>
          </div>
        ) : filteredJobs.length === 0 ? (
          <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-slate-800 py-16 text-center text-slate-500">
            <Briefcase className="h-8 w-8 text-slate-600 mb-2" />
            <p className="text-sm font-medium text-slate-400">No hay ofertas en esta sección</p>
            <p className="text-xs text-slate-500 mt-1 max-w-[240px]">
              {activeTab === "new"
                ? "El scraper buscará nuevas ofertas en su próxima corrida programada."
                : "Las ofertas aquí se limpian automáticamente tras 24 horas."}
            </p>
          </div>
        ) : (
          filteredJobs.map((job) => (
            <article
              key={job.id}
              className="rounded-2xl border border-slate-800/80 bg-slate-900/60 p-4 shadow-sm transition hover:border-slate-700 backdrop-blur-sm"
            >
              {/* CABECERA DE LA TARJETA */}
              <div className="flex items-center justify-between text-[11px] mb-2">
                <span className={`flex items-center gap-1 rounded-md px-2 py-0.5 font-semibold uppercase tracking-wider ${
                  job.source.toLowerCase() === "computrabajo"
                    ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                    : job.source.toLowerCase() === "bumeran"
                    ? "bg-fuchsia-500/10 text-fuchsia-400 border border-fuchsia-500/20"
                    : "bg-blue-500/10 text-blue-400 border border-blue-500/20"
                }`}>
                  <Globe className="h-3 w-3" />
                  {job.source}
                </span>
                <span className="flex items-center gap-1 text-slate-400">
                  <Clock className="h-3 w-3" />
                  {job.published_time_text}
                </span>
              </div>

              {/* TÍTULO Y EMPRESA */}
              <h2 className="text-base font-bold text-white line-clamp-2 leading-snug">
                {job.title}
              </h2>
              <div className="mt-2 flex flex-col gap-1 text-xs text-slate-400">
                <span className="flex items-center gap-1.5 font-medium text-slate-300">
                  <Building2 className="h-3.5 w-3.5 text-slate-500 flex-shrink-0" />
                  {job.company}
                </span>
                <span className="flex items-center gap-1.5">
                  <MapPin className="h-3.5 w-3.5 text-slate-500 flex-shrink-0" />
                  {job.location}
                </span>
              </div>

              {/* ACCIONES DE LA TARJETA */}
              <div className="mt-4 flex items-center gap-2 pt-3 border-t border-slate-800/60">
                {/* Botón Vista Previa */}
                <button
                  onClick={() => setPreviewJob(job)}
                  className="flex flex-1 items-center justify-center gap-1.5 rounded-xl border border-slate-700 bg-slate-800/80 py-2.5 text-xs font-semibold text-slate-200 transition hover:bg-slate-700 active:scale-95"
                >
                  <Eye className="h-3.5 w-3.5" />
                  Vista Previa
                </button>

                {/* Botón Postularme */}
                {job.status === "new" && (
                  <>
                    <a
                      href={job.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={() => updateJobStatus(job.id, "applied")}
                      className="flex flex-1 items-center justify-center gap-1.5 rounded-xl bg-emerald-500 py-2.5 text-xs font-semibold text-slate-950 transition hover:bg-emerald-400 active:scale-95"
                    >
                      <ExternalLink className="h-3.5 w-3.5" />
                      Postularme
                    </a>
                    <button
                      onClick={() => updateJobStatus(job.id, "discarded")}
                      title="Descartar"
                      className="flex h-9 w-9 items-center justify-center rounded-xl border border-slate-800 bg-slate-800/50 text-slate-400 hover:text-rose-400 transition active:scale-95"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </>
                )}

                {job.status === "applied" && (
                  <a
                    href={job.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex flex-1 items-center justify-center gap-1.5 rounded-xl border border-emerald-500/30 bg-emerald-500/10 py-2.5 text-xs font-semibold text-emerald-400"
                  >
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    Ver aviso oficial
                  </a>
                )}

                {job.status === "discarded" && (
                  <button
                    onClick={() => updateJobStatus(job.id, "applied")}
                    className="flex flex-1 items-center justify-center gap-1.5 rounded-xl border border-slate-700 bg-slate-800 py-2.5 text-xs font-medium text-slate-300"
                  >
                    Restaurar a Postuladas
                  </button>
                )}
              </div>
            </article>
          ))
        )}
      </section>

      {/* MODAL / DRAWER DE VISTA PREVIA COMPLETA */}
      {previewJob && (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/70 backdrop-blur-sm p-0 sm:items-center sm:p-4">
          <div className="w-full max-w-lg rounded-t-3xl sm:rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl max-h-[85vh] flex flex-col animate-in slide-in-from-bottom duration-200">
            {/* Header del Modal */}
            <div className="flex items-start justify-between border-b border-slate-800 pb-3">
              <div>
                <span className={`rounded px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${
                  previewJob.source.toLowerCase() === "computrabajo"
                    ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                    : previewJob.source.toLowerCase() === "bumeran"
                    ? "bg-fuchsia-500/10 text-fuchsia-400 border border-fuchsia-500/20"
                    : "bg-blue-500/10 text-blue-400 border border-blue-500/20"
                }`}>
                  {previewJob.source}
                </span>
                <h2 className="mt-1 text-base font-bold text-white">{previewJob.title}</h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  {previewJob.company} • {previewJob.location}
                </p>
              </div>
              <button
                onClick={() => setPreviewJob(null)}
                className="h-7 w-7 rounded-full bg-slate-800 text-slate-400 hover:text-white flex items-center justify-center"
              >
                ✕
              </button>
            </div>

            {/* Contenido / Requisitos */}
            <div className="my-4 overflow-y-auto pr-1 text-xs text-slate-300 leading-relaxed space-y-3">
              <div className="rounded-xl bg-slate-950 p-4 border border-slate-800/80">
                <h3 className="font-semibold text-slate-200 mb-2 text-xs">Resumen del aviso:</h3>
                <p className="whitespace-pre-wrap">{previewJob.full_description || "Sin descripción disponible."}</p>
              </div>
              <div className="flex items-center gap-2 text-slate-400 text-[11px]">
                <Clock className="h-3 w-3" />
                <span>Tiempo de publicación: {previewJob.published_time_text}</span>
              </div>
            </div>

            {/* Acciones del Modal */}
            <div className="pt-3 border-t border-slate-800 flex gap-2">
              <a
                href={previewJob.url}
                target="_blank"
                rel="noopener noreferrer"
                onClick={() => updateJobStatus(previewJob.id, "applied")}
                className="flex-1 rounded-xl bg-emerald-500 py-3 text-center text-xs font-bold text-slate-950 hover:bg-emerald-400 transition capitalize"
              >
                Ir a Postularme en {previewJob.source}
              </a>
              {previewJob.status === "new" && (
                <button
                  onClick={() => updateJobStatus(previewJob.id, "discarded")}
                  className="rounded-xl border border-slate-700 bg-slate-800 px-4 text-xs font-semibold text-slate-300 hover:bg-slate-700 transition"
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
