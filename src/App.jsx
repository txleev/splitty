import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { ArrowLeft, Check } from 'lucide-react';

// Comprehensive mock fallback data for 30+ attendees
const MOCK_FALLBACK_PEOPLE = [
  { id: 'p1', name: 'Emma Davis' },
  { id: 'p2', name: 'Liam Smith' },
  { id: 'p3', name: 'Olivia Johnson' },
  { id: 'p4', name: 'Noah Williams' },
  { id: 'p5', name: 'Sophia Brown' },
  { id: 'p6', name: 'James Jones' },
  { id: 'p7', name: 'Ava Garcia' },
  { id: 'p8', name: 'Lucas Miller' },
  { id: 'p9', name: 'Isabella Davis' },
  { id: 'p10', name: 'Mason Rodriguez' },
  { id: 'p11', name: 'Mia Martinez' },
  { id: 'p12', name: 'Ethan Hernandez' },
  { id: 'p13', name: 'Charlotte Lopez' },
  { id: 'p14', name: 'Alexander Gonzalez' },
  { id: 'p15', name: 'Harper Wilson' },
  { id: 'p16', name: 'Daniel Anderson' },
  { id: 'p17', name: 'Evelyn Thomas' },
  { id: 'p18', name: 'Henry Taylor' },
  { id: 'p19', name: 'Abigail Moore' },
  { id: 'p20', name: 'Jackson Martin' },
  { id: 'p21', name: 'Emily Jackson' },
  { id: 'p22', name: 'Sebastian Lee' },
  { id: 'p23', name: 'Ella Perez' },
  { id: 'p24', name: 'Jack Thompson' },
  { id: 'p25', name: 'Avery White' },
  { id: 'p26', name: 'Matthew Harris' },
  { id: 'p27', name: 'Camila Sanchez' },
  { id: 'p28', name: 'Samuel Clark' },
  { id: 'p29', name: 'Scarlett Ramirez' },
  { id: 'p30', name: 'David Lewis' },
  { id: 'p31', name: 'Victoria Robinson' },
  { id: 'p32', name: 'Joseph Walker' }
];

const MOCK_FALLBACK_ITEMS = [
  { id: 'item-1', name: 'Truffle Parmesan Fries', price: 12.50, ownerId: null },
  { id: 'item-2', name: 'Wood-fired Margherita', price: 18.00, ownerId: null },
  { id: 'item-3', name: 'Prime Ribeye 12oz', price: 38.50, ownerId: null },
  { id: 'item-4', name: 'Spicy Tuna Crispy Rice', price: 16.00, ownerId: null },
  { id: 'item-5', name: 'Classic Caesar Salad', price: 14.00, ownerId: null },
  { id: 'item-6', name: 'Crispy Calamari Fritti', price: 15.50, ownerId: null },
  { id: 'item-7', name: 'Hazy IPA Draft Beer', price: 8.50, ownerId: null },
  { id: 'item-8', name: 'Pinot Noir (Glass)', price: 13.00, ownerId: null },
  { id: 'item-9', name: 'San Pellegrino 750ml', price: 6.00, ownerId: null },
  { id: 'item-10', name: 'Wagyu Beef Sliders', price: 21.00, ownerId: null },
  { id: 'item-11', name: 'Wild Mushroom Risotto', price: 24.50, ownerId: null },
  { id: 'item-12', name: 'Iced Matcha Oat Latte', price: 7.00, ownerId: null },
  { id: 'item-13', name: 'Molten Chocolate Cake', price: 11.00, ownerId: null },
  { id: 'item-14', name: 'Artisan Espresso', price: 4.50, ownerId: null },
  { id: 'item-15', name: 'Tiramisu Della Nonna', price: 10.00, ownerId: null }
];

/* ==========================================================================
   1. FRIEND HOMEPAGE PLACEHOLDER
   ========================================================================== */
function FriendHomepagePlaceholder({ onGoToSorter }) {
  return (
    <div className="placeholder-container">
      <div className="placeholder-card">
        <div className="placeholder-icon">🧾</div>
        <h2 className="placeholder-title">Splitty Homepage</h2>
        <p className="placeholder-desc">
          Space reserved for teammate's homepage merge. Ready to sort the receipt?
        </p>
        <button
          type="button"
          className="btn-go-sorter"
          onClick={onGoToSorter}
        >
          Go to Sorter
        </button>
      </div>
    </div>
  );
}

/* ==========================================================================
   4. RESULTS VIEW COMPONENT
   ========================================================================== */
function ResultsView({ items, people, onBackToSorter }) {
  // Filter people who have at least one assigned item
  const peopleWithAssignedItems = useMemo(() => {
    return people
      .map(person => {
        const assignedItems = items.filter(item => item.ownerId === person.id);
        const subtotal = assignedItems.reduce((acc, it) => acc + Number(it.price || 0), 0);
        const tax = subtotal * 0.088; // 8.8% Tax
        const tip = subtotal * 0.20;  // 20% Tip
        const grandTotal = subtotal + tax + tip;

        return {
          person,
          assignedItems,
          subtotal,
          tax,
          tip,
          grandTotal
        };
      })
      .filter(entry => entry.assignedItems.length > 0);
  }, [items, people]);

  // Overall totals calculation
  const overallTotals = useMemo(() => {
    const subtotal = items.reduce((acc, it) => acc + (it.ownerId ? Number(it.price || 0) : 0), 0);
    const tax = subtotal * 0.088;
    const tip = subtotal * 0.20;
    const grandTotal = subtotal + tax + tip;
    return { subtotal, tax, tip, grandTotal };
  }, [items]);

  return (
    <div className="results-container">
      {/* Header with Centered Headline */}
      <header className="results-header">
        <button
          type="button"
          className="back-btn"
          onClick={onBackToSorter}
          title="Return to Sorter"
        >
          <ArrowLeft size={16} />
          <span>Back to Sorter</span>
        </button>
        <h2 className="results-title">Final Breakdown</h2>
      </header>

      <div className="results-scroll-content">
        {/* Overall Summary Card */}
        <div className="results-overview-card">
          <span className="overview-header">Party Grand Total (Tax & Tip Incl.)</span>
          <span className="overview-grand-total">
            ${overallTotals.grandTotal.toFixed(2)}
          </span>
          <div className="overview-details-row">
            <span>Subtotal: ${overallTotals.subtotal.toFixed(2)}</span>
            <span>8.8% Tax: ${overallTotals.tax.toFixed(2)}</span>
            <span>20% Tip: ${overallTotals.tip.toFixed(2)}</span>
          </div>
        </div>

        {/* Per-Person Itemized Breakdowns */}
        {peopleWithAssignedItems.length === 0 ? (
          <div className="results-empty-state">
            <p>No items have been assigned yet.</p>
            <button type="button" className="btn-go-sorter" onClick={onBackToSorter}>
              Return to Assign Items
            </button>
          </div>
        ) : (
          peopleWithAssignedItems.map(({ person, assignedItems, subtotal, tax, tip, grandTotal }) => (
            <div key={person.id} className="person-breakdown-card">
              <div className="person-card-header">
                <div className="person-info-group">
                  <div className="person-avatar-mini">
                    {person.name?.charAt(0).toUpperCase() || '?'}
                  </div>
                  <div>
                    <h3 className="person-card-name">{person.name}</h3>
                    <span className="person-items-count">
                      {assignedItems.length} {assignedItems.length === 1 ? 'item' : 'items'}
                    </span>
                  </div>
                </div>
              </div>

              {/* List of assigned items and prices */}
              <div className="assigned-items-list">
                {assignedItems.map(item => (
                  <div key={item.id} className="item-breakdown-row">
                    <span className="item-row-name">{item.name}</span>
                    <span className="item-row-price">${Number(item.price || 0).toFixed(2)}</span>
                  </div>
                ))}
              </div>

              {/* Financial Calculation breakdown: Subtotal, 8.8% Tax, 20% Tip, Grand Total */}
              <div className="calculation-breakdown-table">
                <div className="calc-row">
                  <span>Subtotal</span>
                  <span className="calc-row-val">${subtotal.toFixed(2)}</span>
                </div>
                <div className="calc-row">
                  <span>Tax (8.8%)</span>
                  <span className="calc-row-val">${tax.toFixed(2)}</span>
                </div>
                <div className="calc-row">
                  <span>Tip (20%)</span>
                  <span className="calc-row-val">${tip.toFixed(2)}</span>
                </div>
                {/* Grand Total prominently in --light-green */}
                <div className="calc-row grand-total">
                  <span>Grand Total</span>
                  <span className="calc-row-val">${grandTotal.toFixed(2)}</span>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

/* ==========================================================================
   3. INTERACTIVE SORTER COMPONENT (Mic, Camera & Demo Tag Removed)
   ========================================================================== */
function InteractiveSorter({
  items,
  people,
  draggedOverId,
  isLoading,
  isDragging,
  toastFeedback,
  onBack,
  onResetDemo,
  onDragStart,
  onDragEnd,
  onDragOver,
  onDragLeave,
  onDrop
}) {
  const [showResults, setShowResults] = useState(false);
  const scrollContainerRef = useRef(null);

  // Calculate unassigned items and target item
  const unassignedItems = useMemo(() => {
    return items.filter(item => !item.ownerId);
  }, [items]);

  const currentItem = unassignedItems[0] || null;
  const itemsLeftCount = unassignedItems.length;
  const totalItemsCount = items.length;
  const sortedCount = totalItemsCount - itemsLeftCount;

  // Split people array in half: left column and right column
  const { leftPeople, rightPeople } = useMemo(() => {
    const half = Math.ceil(people.length / 2);
    return {
      leftPeople: people.slice(0, half),
      rightPeople: people.slice(half)
    };
  }, [people]);

  // Person stats for badges and totals
  const personStats = useMemo(() => {
    const stats = {};
    for (const p of people) {
      stats[p.id] = { count: 0, total: 0 };
    }
    for (const item of items) {
      if (item.ownerId && stats[item.ownerId]) {
        stats[item.ownerId].count += 1;
        stats[item.ownerId].total += Number(item.price || 0);
      }
    }
    return stats;
  }, [people, items]);

  // Auto-scrolling: If cursor/touch is within 100px of top or bottom bounds while dragging, adjust scrollTop +/- 12px
  const handleContainerDragOver = (e) => {
    e.preventDefault();
    const container = scrollContainerRef.current;
    if (!container) return;

    const rect = container.getBoundingClientRect();
    const clientY = e.clientY;

    const topThreshold = rect.top + 100;
    const bottomThreshold = rect.bottom - 100;

    if (clientY < topThreshold) {
      container.scrollTop -= 12;
    } else if (clientY > bottomThreshold) {
      container.scrollTop += 12;
    }
  };

  // Render Person Avatar Node
  const renderAvatarNode = (person, side) => {
    const isOver = draggedOverId === person.id;
    const stats = personStats[person.id] || { count: 0, total: 0 };
    const firstInitial = (person.name && person.name.trim().length > 0)
      ? person.name.trim().charAt(0).toUpperCase()
      : '?';

    return (
      <div
        key={person.id}
        id={`avatar-node-${person.id}`}
        className="avatar-node"
        onDragOver={(e) => onDragOver(e, person.id)}
        onDragLeave={(e) => onDragLeave(e, person.id)}
        onDrop={(e) => onDrop(e, person.id)}
        title={`Drop here to assign to ${person.name}`}
      >
        <div className={`avatar-circle ${isOver ? 'drag-over' : ''}`}>
          <span className="avatar-initial">{firstInitial}</span>
          {stats.count > 0 && (
            <span className="avatar-badge-count">{stats.count}</span>
          )}
        </div>

        <div className="avatar-meta">
          <span className="avatar-name">{person.name}</span>
          <span className={`avatar-total ${stats.count > 0 ? 'has-items' : ''}`}>
            {stats.count > 0 ? `$${stats.total.toFixed(2)}` : '0 items'}
          </span>
        </div>
      </div>
    );
  };

  // If showResults is true, hide sorter and render ResultsView
  if (showResults) {
    return (
      <ResultsView
        items={items}
        people={people}
        onBackToSorter={() => setShowResults(false)}
      />
    );
  }

  return (
    <div className="sorter-container">
      {/* Sorter Header with Centered Headline */}
      <header className="sorter-header">
        <div className="sorter-header-top">
          <button 
            type="button" 
            className="back-btn" 
            onClick={onBack}
            title="Return to Homepage"
          >
            <ArrowLeft size={16} />
            <span>Back</span>
          </button>

          <div className="sorter-title-group">
            <h2 className="sorter-title">Receipt Sorter</h2>
          </div>
        </div>

        <div className="sorter-progress-row">
          <span>{sortedCount} of {totalItemsCount} sorted</span>
          <span>{people.length} people</span>
        </div>

        <div className="progress-bar-bg">
          <div 
            className="progress-bar-fill" 
            style={{ width: `${totalItemsCount > 0 ? (sortedCount / totalItemsCount) * 100 : 0}%` }} 
          />
        </div>
      </header>

      {/* Action feedback toast */}
      {toastFeedback && (
        <div className="toast-feedback">
          <span>✨</span>
          <span>{toastFeedback}</span>
        </div>
      )}

      {/* Loading state */}
      {isLoading ? (
        <div className="loading-container">
          <div className="spinner" />
          <p>Loading session data...</p>
        </div>
      ) : (
        /* Scrollable Table with Auto-Scrolling on drag over */
        <div 
          className="table-scroll-container" 
          id="scrollable-table"
          ref={scrollContainerRef}
          onDragOver={handleContainerDragOver}
        >
          <div className="split-table-layout">
            
            {/* Left Column (First Half of People) */}
            <div className="avatar-column left" id="column-left">
              {leftPeople.map(person => renderAvatarNode(person, 'left'))}
            </div>

            {/* Center Drag Guideline */}
            <div className="center-corridor" aria-hidden="true">
              <div className="corridor-dashed-line" />
            </div>

            {/* Right Column (Second Half of People) */}
            <div className="avatar-column right" id="column-right">
              {rightPeople.map(person => renderAvatarNode(person, 'right'))}
            </div>

          </div>
        </div>
      )}

      {/* The Item Dock (Drag Source at Bottom Center - Mic removed) */}
      <section className="item-dock-container" id="item-dock">
        <div className="dock-content">
          {itemsLeftCount > 0 && currentItem ? (
            <>
              <div className="dock-hint">
                <span>Drag to an avatar above</span>
              </div>

              {/* The draggable item circle with --purple border & glow */}
              <div
                id={`docked-item-${currentItem.id}`}
                className={`dock-item-circle ${isDragging ? 'is-dragging' : ''}`}
                draggable="true"
                onDragStart={onDragStart}
                onDragEnd={onDragEnd}
                title={`Drag ${currentItem.name} to any person avatar`}
              >
                <span className="dock-item-price">${Number(currentItem.price || 0).toFixed(2)}</span>
                <span className="dock-item-drag-icon">⋮⋮</span>
              </div>

              <div className="dock-item-details">
                <p className="dock-item-name">{currentItem.name}</p>
                <p className="dock-items-left-text">
                  <span>{itemsLeftCount}</span> {itemsLeftCount === 1 ? 'Item left' : 'Items left'}
                </p>
              </div>
            </>
          ) : (
            /* Completion: When 0 items left, replace draggable item with View Results Breakdown */
            <div className="dock-completed-container">
              <div className="completed-badge">
                <Check size={18} strokeWidth={3} />
                <span>All items assigned!</span>
              </div>
              <button 
                type="button" 
                className="btn-view-results" 
                onClick={() => setShowResults(true)}
              >
                View Results Breakdown
              </button>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}

/* ==========================================================================
   MAIN APP ROOT
   ========================================================================== */
export default function App() {
  // Navigation State: 'home' by default so teammate can drop in their homepage
  const [currentView, setCurrentView] = useState('home');

  // Dynamic state for interactive sorter
  const [items, setItems] = useState([]);
  const [people, setPeople] = useState([]);
  const [draggedOverId, setDraggedOverId] = useState(null);

  const [isLoading, setIsLoading] = useState(true);
  const [isDragging, setIsDragging] = useState(false);
  const [toastFeedback, setToastFeedback] = useState(null);

  // Backend Integration: Data Fetching on mount (DO NOT BREAK)
  const fetchSessionData = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await fetch('http://localhost:8000/api/session-data');
      if (!response.ok) {
        throw new Error(`Server returned HTTP ${response.status}`);
      }
      const data = await response.json();
      setPeople(Array.isArray(data.people) ? data.people : []);
      setItems(Array.isArray(data.items) ? data.items : []);
    } catch (error) {
      console.warn('FastAPI backend offline, loading mock fallback data:', error.message);
      setPeople(MOCK_FALLBACK_PEOPLE);
      setItems(MOCK_FALLBACK_ITEMS);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSessionData();
  }, [fetchSessionData]);

  // Derived current target item for drag start
  const currentItem = useMemo(() => {
    return items.find(item => !item.ownerId) || null;
  }, [items]);

  // HTML5 Drag and Drop Handlers (DO NOT BREAK)
  const handleDragStart = (e) => {
    if (!currentItem) return;
    setIsDragging(true);
    e.dataTransfer.setData('text/plain', currentItem.id);
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragEnd = () => {
    setIsDragging(false);
    setDraggedOverId(null);
  };

  const handleDragOver = (e, personId) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    if (draggedOverId !== personId) {
      setDraggedOverId(personId);
    }
  };

  const handleDragLeave = (e, personId) => {
    if (e.currentTarget.contains(e.relatedTarget)) {
      return;
    }
    if (draggedOverId === personId) {
      setDraggedOverId(null);
    }
  };

  const handleDrop = async (e, personId) => {
    e.preventDefault();
    setDraggedOverId(null);
    setIsDragging(false);

    if (!currentItem) return;

    const assignedItemId = currentItem.id;
    const assignedItemName = currentItem.name;
    const targetPerson = people.find(p => p.id === personId);

    // Optimistic UI update: instantly update ownerId
    setItems(prevItems =>
      prevItems.map(item =>
        item.id === assignedItemId ? { ...item, ownerId: personId } : item
      )
    );

    setToastFeedback(`Assigned "${assignedItemName}" to ${targetPerson?.name?.split(' ')[0] || 'person'}`);
    setTimeout(() => setToastFeedback(null), 2500);

    // Backend Integration Data Sync: POST http://localhost:8000/api/assign
    try {
      const response = await fetch('http://localhost:8000/api/assign', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          itemId: assignedItemId,
          ownerId: personId
        })
      });

      if (!response.ok) {
        console.warn(`Sync warning: Server returned status ${response.status}`);
      }
    } catch (err) {
      console.info('Backend POST sync note: FastAPI server offline, saved in optimistic UI.');
    }
  };

  const handleResetDemo = () => {
    setItems(prev => prev.map(item => ({ ...item, ownerId: null })));
    setToastFeedback('Receipt reset! Ready to sort.');
    setTimeout(() => setToastFeedback(null), 2000);
  };

  return (
    <div className="viewport-wrapper">
      <main className="mobile-frame" id="splitty-app">
        {/* Conditional View Rendering based on currentView */}
        {currentView === 'home' ? (
          <FriendHomepagePlaceholder onGoToSorter={() => setCurrentView('sorter')} />
        ) : (
          <InteractiveSorter
            items={items}
            people={people}
            draggedOverId={draggedOverId}
            isLoading={isLoading}
            isDragging={isDragging}
            toastFeedback={toastFeedback}
            onBack={() => setCurrentView('home')}
            onResetDemo={handleResetDemo}
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          />
        )}
      </main>
    </div>
  );
}
