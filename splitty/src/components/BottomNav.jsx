
import { Keyboard, Camera, Mic, Users } from "lucide-react";

function BottomNav({ activeTab, onTabChange }) {
  const navItems = [
    { id: "voice", icon: Mic, label: "Voice", position: "top" },
    { id: "camera", icon: Camera, label: "Camera", position: "left" },
    { id: "keyboard", icon: Keyboard, label: "Keyboard", position: "right" },
    { id: "people", icon: Users, label: "People", position: "bottom" },
  ];

  return (
    <nav className="direction-nav" aria-label="Main navigation">
      {navItems.map((item) => {
        const Icon = item.icon;

        return (
          <button
            key={item.id}
            type="button"
            className={`direction-button ${item.position} ${
              activeTab === item.id ? "active" : ""
            }`}
            onClick={() => onTabChange(item.id)}
            aria-label={item.label}
            aria-pressed={activeTab === item.id}
            title={item.label}
          >
            <Icon size={24} strokeWidth={1.8} />
          </button>
        );
      })}
    </nav>
  );
}

export default BottomNav;
