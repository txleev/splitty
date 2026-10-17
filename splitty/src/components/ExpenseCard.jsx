
function ExpenseCard({ expense }) {
  return (
    <div className="expense-row">
      <div className="timeline">
        <span
          className="timeline-dot"
          style={{ backgroundColor: expense.color }}
        />
      </div>

      <div className="expense-card">
        <div className="expense-info">
          <h3>{expense.title}</h3>

          <p>
            {expense.group} · {expense.date}
          </p>

          <span className="expense-amount">
            €{expense.amount.toFixed(2)}
          </span>
        </div>

        <div className="avatars">
          {expense.members.slice(0, 3).map((member) => (
            <div
              className="avatar"
              key={member}
              title={member}
            >
              {member.charAt(0)}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default ExpenseCard;