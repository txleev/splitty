
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
} from "recharts";

function ExpenseChart({ expenses }) {
  const data = expenses.map((expense) => ({
    name: expense.title,
    value: expense.amount,
    color: expense.color,
  }));

  return (
    <div className="chart-container">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            outerRadius={52}
            dataKey="value"
            stroke="#242326"
            strokeWidth={3}
            isAnimationActive={false}
          >
            {data.map((entry) => (
              <Cell
                key={entry.name}
                fill={entry.color}
              />
            ))}
          </Pie>

          <Tooltip
            formatter={(value) => `€${value.toFixed(2)}`}
            contentStyle={{
                backgroundColor: "#3C3744",
                border: "1px solid #9F12FF",
                borderRadius: "10px",
            }}
            itemStyle={{
                color: "#9F12FF",
            }}
            labelStyle={{
                color: "#FBFFF1",
            }}
            />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}

export default ExpenseChart;