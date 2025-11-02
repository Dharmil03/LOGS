import React from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip } from 'recharts';

export default function MetricsChart({ data }) {
  const values = data?.data?.result || [];
  const chartData = values.map((d, i) => ({ name: `Metric ${i}`, value: d.value[1] }));

  return (
    <div>
      <h3>CPU Metrics</h3>
      <LineChart width={500} height={250} data={chartData}>
        <Line type="monotone" dataKey="value" stroke="#82ca9d" />
        <XAxis dataKey="name" />
        <YAxis />
        <Tooltip />
      </LineChart>
    </div>
  );
}
