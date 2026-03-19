"use client";

import React, { useMemo } from "react";
import ReactECharts from "echarts-for-react";

export interface Agent {
  id: string;
  name: string;
  profile: string;
  color: string;
  is_human: boolean;
  last_speech?: string;
}

export interface Edge {
  source: string;
  target: string;
  value: number;
}

interface EChartsGraphProps {
  agents: Agent[];
  edges: Edge[];
}

// 辅助函数：插值计算边的颜色（蓝色 -> 橙色）
function interpolateColor(value: number) {
  const t = Math.min(1, value / 10);
  const r = Math.round(0 + t * 255);
  const g = Math.round(212 - t * 130);
  const b = Math.round(255 - t * 220);
  return `rgb(${r},${g},${b})`;
}

export default function EChartsGraph({ agents, edges }: EChartsGraphProps) {
  const option = useMemo(() => {
    const nodes = agents.map((a) => ({
      id: a.id,
      name: a.name,
      value: a.last_speech || a.name,
      symbolSize: a.is_human ? 54 : 38,
      symbol: a.is_human ? "diamond" : "circle",
      label: {
        show: true,
        fontSize: a.is_human ? 13 : 11,
        fontWeight: a.is_human ? "bold" : "normal",
        color: "#e2e8f0",
        formatter: () => a.name,
      },
      itemStyle: {
        color: a.color || "#00d4ff",
        borderColor: a.is_human ? "#FFD700" : "rgba(255,255,255,0.2)",
        borderWidth: a.is_human ? 3 : 1,
        shadowBlur: a.is_human ? 30 : 12,
        shadowColor: a.is_human ? "#FFD700" : (a.color || "#00d4ff"),
      },
      tooltip: {
        formatter: () => {
          return `<b style="color:${a.color}">${a.name}</b><br/>
                  <span style="font-size:11px;color:#94a3b8">${
                    a.last_speech || "等待发言..."
                  }</span>`;
        },
      },
    }));

    const links = edges.map((e) => ({
      source: e.source,
      target: e.target,
      value: e.value,
      lineStyle: {
        width: Math.max(1, e.value * 1.5),
        color: interpolateColor(e.value),
        opacity: Math.min(0.9, 0.3 + e.value * 0.1),
        curveness: 0.15,
      },
    }));

    return {
      backgroundColor: "transparent",
      tooltip: { trigger: "item", confine: true },
      animationDurationUpdate: 800,
      animationEasingUpdate: "quinticInOut",
      series: [
        {
          type: "graph",
          layout: "force",
          roam: true,
          draggable: true,
          data: nodes,
          links: links,
          force: {
            repulsion: 300,
            attraction: 0.04,
            gravity: 0.1,
            edgeLength: [120, 280],
            layoutAnimation: true,
          },
          emphasis: {
            focus: "adjacency",
            lineStyle: { width: 8 },
          },
          lineStyle: { color: "source", curveness: 0.15 },
          label: { position: "bottom" },
          edgeLabel: {
            show: false,
          },
        },
      ],
    };
  }, [agents, edges]);

  return (
    <ReactECharts
      option={option}
      style={{ height: "100%", width: "100%" }}
      opts={{ renderer: "canvas" }}
      theme="dark"
      lazyUpdate
    />
  );
}
