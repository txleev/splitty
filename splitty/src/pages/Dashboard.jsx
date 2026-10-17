
import { useState } from "react";
import { CheckCheck } from "lucide-react";

import ExpenseChart from "../components/ExpenseChart";
import ExpenseCard from "../components/ExpenseCard";
import BottomNav from "../components/BottomNav";

import { expenses, currentUser } from "../data/expenses";

function Dashboard() {
  const [activeTab, setActiveTab] = useState("profile");

  // Calculate the total expenses
  const totalExpenses = expenses.reduce(
    (total, expense) => total + expense.amount,
    0
  );

  // Calculate how much the current user owes
  const amountOwed = expenses.reduce((total, expense) => {
    const isMember = expense.members.includes(currentUser);

    if (!isMember || expense.paidBy === currentUser) {
      return total;
    }

    const share = expense.amount / expense.members.length;

    return total + share;
  }, 0);

  // Calculate how much other people owe the current user
  const amountToReceive = expenses.reduce((total, expense) => {
    if (expense.paidBy !== currentUser) {
      return total;
    }

    const share = expense.amount / expense.members.length;

    return total + expense.amount - share;
  }, 0);

  return (
    <div className="dashboard">

      {/* Header */}
      <header className="dashboard-header">
        <h1>Splitty</h1>

        <button
          className="header-action"
          type="button"
          aria-label="All expenses"
          title="All expenses"
          onClick={() =>
            document
              .getElementById("expenses")
              ?.scrollIntoView({ behavior: "smooth" })
          }
        >
          <CheckCheck size={28} strokeWidth={1.8} />
        </button>
      </header>

      {/* Chart */}
      <section className="chart-section">
        <ExpenseChart expenses={expenses} />

        <p className="chart-caption">
          Total shared expenses
        </p>

        <h2 className="total-amount">
          €{totalExpenses.toFixed(2)}
        </h2>
      </section>

      {/* Balance */}
      <section className="balance-card">
        <p className="balance-label">Amount owed:</p>

        <h2>€{amountOwed.toFixed(2)}</h2>

        <div className="balance-divider"></div>

        <div className="balance-footer">
          <span>Others owe you</span>

          <span className="receive-amount">
            €{amountToReceive.toFixed(2)}
          </span>
        </div>
      </section>

      {/* Expenses */}
      <section className="expenses-section" id="expenses">
        <div className="section-header">
            <h2>Expenses</h2>
            <span>{expenses.length} items</span>
        </div>

        <div className="expenses-scroll-area">
            <div className="expense-list">
            {expenses.map((expense) => (
                <ExpenseCard
                key={expense.id}
                expense={expense}
                />
            ))}
            </div>
        </div>
      </section>

      {/* Navigation */}
      <BottomNav
        activeTab={activeTab}
        onTabChange={setActiveTab}
      />

    </div>
  );
}

export default Dashboard;