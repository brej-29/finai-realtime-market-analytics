"use client";

import { Chart as ChartJS, ArcElement, Tooltip, Legend } from "chart.js";
import { Pie } from "react-chartjs-2";

ChartJS.register(ArcElement, Tooltip, Legend);

interface Slice {
  label: string;
  value: number;
}

interface Props {
  slices: Slice[];
}

export function AllocationPie({ slices }: Props) {
  if (!slices.length) {
    return <p className="text-sm text-slate-400">No holdings yet.</p>;
  }

  const data = {
    labels: slices.map((s) => s.label),
    datasets: [
      {
        data: slices.map((s) => s.value),
        backgroundColor: ["#22C55E", "#0EA5E9", "#F97316", "#6366F1", "#E11D48"],
        borderWidth: 0
      }
    ]
  };

  return (
    <div className="h-64 w-full">
      <Pie data={data} />
    </div>
  );
}