"use client";

import { useEffect, useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Sparkles, TerminalSquare, Zap, Play, RotateCcw, User } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";

import EChartsGraph, { Agent, Edge } from "@/components/EChartsGraph";

const API = "http://localhost:8000";

interface Tribe {
  tribe_id: number;
  tribe_name: string;
  has_human: boolean;
  members: { name: string; color: string; is_human: boolean }[];
}

export default function Home() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [topic, setTopic] = useState("等待世界议题注入...");
  const [currentTick, setCurrentTick] = useState(0);
  const [maxTicks, setMaxTicks] = useState(5);
  const [logs, setLogs] = useState<any[]>([]);
  const [tribes, setTribes] = useState<Tribe[]>([]);
  const [showModal, setShowModal] = useState(false);
  const [isEvolving, setIsEvolving] = useState(false);
  const [explosionActive, setExplosionActive] = useState(false);

  const scrollRef = useRef<HTMLDivElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    // Initial fetch to check status
    fetch(`${API}/api/sandbox/state`)
      .then((res) => res.json())
      .then((data) => {
        if (data.agents && data.agents.length > 0) {
          setAgents(data.agents);
          setEdges(data.edges || []);
          setCurrentTick(data.current_tick);
        }
      })
      .catch(() => {});
  }, []);

  const addLog = (log: any) => {
    setLogs((prev) => [...prev, log]);
    setTimeout(() => {
      if (scrollRef.current) {
        scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
      }
    }, 50);
  };

  const startStream = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }
    const es = new EventSource(`${API}/api/sandbox/stream`);
    eventSourceRef.current = es;

    es.onmessage = (e) => {
      const event = JSON.parse(e.data);
      handleEvent(event);
    };

    es.onerror = () => {
      toast.error("SSE Connection lost. Switching to polling...");
      es.close();
    };
  };

  const handleEvent = (event: any) => {
    switch (event.type) {
      case "init":
        setTopic(event.topic);
        setAgents(event.agents.map((a: any) => ({ ...a, last_speech: "" })));
        setEdges([]);
        setTribes([]);
        setShowModal(false);
        addLog({
          icon: "🌏",
          name: "System",
          speech: `世界议题已投放 -> ${event.topic}`,
          color: "#7c3aed",
        });
        // 视觉爆炸效果
        setExplosionActive(true);
        setTimeout(() => setExplosionActive(false), 2000);
        break;
      case "tick_start":
        setCurrentTick(event.tick);
        setMaxTicks(event.max_ticks);
        toast(`Tick ${event.tick}/${event.max_ticks} Started`, {
          icon: "⚡",
          style: { background: "#0f1f3d", borderColor: "#00d4ff" },
        });
        break;
      case "speech":
        setAgents((prev) =>
          prev.map((a) =>
            a.id === event.agent_id
              ? { ...a, last_speech: event.speech }
              : a
          )
        );
        addLog({
          icon: "💬",
          name: event.agent_name,
          speech: event.speech,
          sub: `认同: ${event.agree_with_id}`,
          color: "#0ea5e9",
        });
        break;
      case "matrix_update":
        setEdges(event.edges);
        break;
      case "evolution_complete":
        setIsEvolving(false);
        setTribes(event.tribes);
        setShowModal(true);
        addLog({
          icon: "🎉",
          name: "System",
          speech: "Evolution Complete! Tribes emerged.",
          color: "#FFD700",
        });
        toast.success("部落涌现完成！", {
          style: { background: "#0f1f3d", borderColor: "#FFD700" },
        });
        break;
    }
  };

  const startEvolution = async () => {
    setIsEvolving(true);
    try {
      const res = await fetch(`${API}/api/sandbox/start`, { method: "POST" });
      if (!res.ok) {
        const errorData = await res.json();
        if (errorData.detail?.includes("登录")) {
          // Fallback to demo mode if not initialized
          window.location.href = `${API}/auth/demo`;
          return;
        } else {
          toast.error(errorData.detail || "启动失败");
          setIsEvolving(false);
          return;
        }
      }
      addLog({
        icon: "🚀",
        name: "System",
        speech: "Babel Sandbox Event Loop Started...",
        color: "#00d4ff",
      });
      startStream();
    } catch {
      toast.error("Network Error. Is the backend running?");
      setIsEvolving(false);
    }
  };

  const resetSandbox = async () => {
    await fetch(`${API}/api/sandbox/reset`);
    setAgents([]);
    setEdges([]);
    setCurrentTick(0);
    setLogs([]);
    setTribes([]);
    setShowModal(false);
    setIsEvolving(false);
    setTopic("等待世界议题注入...");
    setExplosionActive(false);
    if (eventSourceRef.current) eventSourceRef.current.close();
  };

  return (
    <main className="flex h-screen w-full flex-col overflow-hidden bg-[#050b18] text-slate-200">
      {/* HEADER */}
      <header className="flex h-16 shrink-0 items-center justify-between border-b border-[#00d4ff]/20 bg-[#0a1628]/80 px-6 backdrop-blur-md z-50">
        <div className="flex items-center gap-3">
          <Sparkles className="h-5 w-5 text-[#00d4ff]" />
          <h1 className="font-mono text-lg font-bold tracking-wider">
            Petri<span className="text-yellow-400">培养皿</span>
          </h1>
          <span className="hidden font-mono text-xs text-slate-500 sm:inline-block">
            Intelligent Hive Experiment
          </span>
        </div>
        <div className="flex items-center gap-4">
          <Badge
            variant="outline"
            className="max-w-[300px] truncate border-purple-500/50 bg-purple-500/10 text-purple-300 md:max-w-[500px]"
          >
            {topic}
          </Badge>
          <div className="font-mono text-sm text-[#00d4ff] flex items-center gap-2">
            <Zap className="h-4 w-4" /> TICK {currentTick}/{maxTicks}
          </div>
        </div>
      </header>

      {/* Progress */}
      <div className="h-1 w-full bg-[#050b18]">
        <motion.div
          className="h-full bg-gradient-to-r from-[#00d4ff] to-purple-500"
          initial={{ width: 0 }}
          animate={{
            width: maxTicks > 0 ? `${(currentTick / maxTicks) * 100}%` : "0%",
          }}
          transition={{ duration: 0.8, ease: "circOut" }}
        />
      </div>

      {/* MAIN CONTENT */}
      <div className="flex flex-1 overflow-hidden">
        {/* GRAPH AREA */}
        <div className="relative flex-1 bg-[radial-gradient(ellipse_at_center,rgba(0,212,255,0.05)_0%,#050b18_70%)]">
          {explosionActive && (
            <motion.div
              initial={{ opacity: 0, scale: 0.5 }}
              animate={{ opacity: [0, 1, 0], scale: [0.5, 2, 3] }}
              transition={{ duration: 1.5, ease: "easeOut" }}
              className="pointer-events-none absolute inset-0 z-0 m-auto h-[400px] w-[400px] rounded-full bg-[#00d4ff] blur-[150px]"
            />
          )}

          <div className="absolute inset-0 z-10 w-full h-full">
            <EChartsGraph agents={agents} edges={edges} />
          </div>

          <div className="pointer-events-none absolute bottom-6 left-1/2 z-20 -translate-x-1/2 animate-pulse font-mono text-xs text-slate-500">
            ⟳ 物理引擎运行中 — 观念相近的 Agent 将自发聚拢
          </div>
        </div>

        {/* SIDE PANELS */}
        <div className="z-30 flex w-[400px] shrink-0 flex-col border-l border-[#00d4ff]/20 bg-[#0a1628]/95 backdrop-blur-xl">
          {/* Controls */}
          <div className="flex flex-col gap-3 border-b border-[#00d4ff]/20 p-5 p-4">
            <div className="flex gap-2">
              <Button
                onClick={startEvolution}
                disabled={isEvolving}
                className="flex-1 bg-gradient-to-r from-sky-500 to-indigo-500 text-white hover:shadow-[0_0_15px_rgba(0,212,255,0.5)] transition-all"
              >
                <Play className="mr-2 h-4 w-4" />{" "}
                {isEvolving ? "演化观测试验中..." : "启动演化引擎"}
              </Button>
              <Button
                variant="outline"
                size="icon"
                onClick={resetSandbox}
                className="border-[#00d4ff]/30 text-[#00d4ff] hover:bg-[#00d4ff]/10"
              >
                <RotateCcw className="h-4 w-4" />
              </Button>
            </div>
            <Button
              variant="secondary"
              className="w-full border border-dashed border-[#00d4ff]/30 bg-[#0f1f3d] text-slate-400 hover:border-[#00d4ff] hover:text-[#00d4ff]"
              onClick={() => (window.location.href = `${API}/auth/login`)}
            >
              <User className="mr-2 h-4 w-4" /> 投入自我人格观测 (SecondMe)
            </Button>
          </div>

          {/* Terminal Console */}
          <div className="flex items-center gap-2 border-b border-[#00d4ff]/20 bg-[#0f1f3d] px-4 py-2 font-mono text-xs text-slate-400">
            <div className="h-2 w-2 animate-pulse rounded-full bg-[#00d4ff] shadow-[0_0_8px_#00d4ff]" />
            SANDBOX CONSOLE — 广场实时流
          </div>
          <div className="flex-1 overflow-y-auto p-4 custom-scrollbar" ref={scrollRef}>
            <div className="flex flex-col gap-4 font-mono text-xs pb-10">
              <AnimatePresence>
                {logs.map((log, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    className="flex flex-col gap-1"
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-slate-500">
                        {new Date().toLocaleTimeString("zh-CN", {
                          hour12: false,
                        })}
                      </span>
                      <span style={{ color: log.color }} className="font-bold">
                        {log.icon} {log.name}
                      </span>
                    </div>
                    <div className="pl-[68px] text-slate-300 leading-relaxed">
                      {log.speech}
                    </div>
                    {log.sub && (
                      <div className="pl-[68px] text-[10px] text-slate-500">
                        {log.sub}
                      </div>
                    )}
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          </div>
        </div>
      </div>

      {/* Tribe Modal (Overlay) */}
      <AnimatePresence>
        {showModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[100] flex items-center justify-center bg-[#050b18]/80 backdrop-blur-md"
          >
            <motion.div
              initial={{ scale: 0.9, y: 20 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.9, y: 20 }}
              className="relative max-w-xl w-[90%] overflow-hidden rounded-2xl border border-[#00d4ff]/50 bg-[#0f1f3d] shadow-[0_0_60px_rgba(0,212,255,0.2)] p-8 text-center"
            >
              {/* background effect inside modal */}
              <div className="absolute top-0 right-0 -m-20 h-40 w-40 rounded-full bg-purple-500/20 blur-3xl mix-blend-screen" />
              <div className="absolute bottom-0 left-0 -m-20 h-40 w-40 rounded-full bg-[#00d4ff]/20 blur-3xl mix-blend-screen" />

              <div className="relative z-10">
                <div className="mb-4 text-5xl drop-shadow-lg">🦠</div>
                <h2 className="mb-6 text-2xl font-bold text-yellow-500 drop-shadow-md tracking-wide">
                  本维演化终止 · 聚类变异完成
                </h2>

                <div className="mb-8 text-slate-300 leading-relaxed text-sm">
                  {tribes.find((t) => t.has_human) ? (
                    <>
                      你在培养皿中的投影经历了 <b>{maxTicks}</b> 轮失控迭代，<br />
                      你的变量最终被以下成分聚拢捕获，形成了变异孢子群：
                      <div className="mt-4 text-xl font-bold text-yellow-400 border-y border-[#00d4ff]/10 py-3 bg-[#0a1628]/50">
                        【{tribes.find((t) => t.has_human)?.tribe_name}】
                      </div>
                    </>
                  ) : (
                    <>实验结束。在本次混沌中，共分化出 {tribes.length} 个独立变异群落。</>
                  )}
                </div>

                <div className="mb-8 flex flex-wrap justify-center gap-2">
                  {tribes.map((tribe) =>
                    tribe.members.map((m, idx) => (
                      <Badge
                        key={`${tribe.tribe_id}-${idx}`}
                        variant="outline"
                        className={`px-3 py-1 bg-black/20 ${
                          m.is_human
                            ? "border-yellow-500 text-yellow-500"
                            : "border-[#00d4ff]/40 text-[#00d4ff]"
                        }`}
                      >
                        {m.is_human && "★ "} {m.name}
                      </Badge>
                    ))
                  )}
                </div>

                <div className="flex justify-center gap-4">
                  <Button
                    onClick={resetSandbox}
                    className="bg-gradient-to-r from-[#00d4ff] to-purple-600 text-white hover:brightness-110 shadow-lg px-6"
                  >
                    🚀 重置变量，开启下轮实验
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => setShowModal(false)}
                    className="border-slate-600 text-slate-300 hover:text-white hover:bg-slate-800"
                  >
                    继续观测标本
                  </Button>
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </main>
  );
}
