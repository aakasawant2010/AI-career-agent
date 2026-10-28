import { NavLink, Outlet } from "react-router-dom";
import {
  LayoutDashboard,
  BriefcaseBusiness,
  FileText,
  BrainCircuit,
  User,
  Settings,
} from "lucide-react";

const navigation = [
  { name: "Dashboard", path: "/", icon: LayoutDashboard },
  { name: "Jobs", path: "/jobs", icon: BriefcaseBusiness },
  { name: "Applications", path: "/applications", icon: FileText },
  { name: "Interviews", path: "/interviews", icon: BrainCircuit },
  { name: "Resume", path: "/resume", icon: FileText },
  { name: "Profile", path: "/profile", icon: User },
];

export default function AppLayout() {
  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <aside className="fixed left-0 top-0 h-screen w-64 border-r border-slate-800 bg-slate-900/80">
        <div className="flex h-16 items-center border-b border-slate-800 px-6">
          <BrainCircuit className="mr-3 h-7 w-7 text-cyan-400" />
          <span className="text-lg font-bold">AI Career Agent</span>
        </div>

        <nav className="space-y-2 p-4">
          {navigation.map((item) => {
            const Icon = item.icon;

            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  `flex items-center rounded-lg px-4 py-3 text-sm font-medium transition ${
                    isActive
                      ? "bg-cyan-500/10 text-cyan-400"
                      : "text-slate-400 hover:bg-slate-800 hover:text-white"
                  }`
                }
              >
                <Icon className="mr-3 h-5 w-5" />
                {item.name}
              </NavLink>
            );
          })}
        </nav>

        <div className="absolute bottom-4 left-4 right-4">
          <button className="flex w-full items-center rounded-lg px-4 py-3 text-sm text-slate-400 hover:bg-slate-800 hover:text-white">
            <Settings className="mr-3 h-5 w-5" />
            Settings
          </button>
        </div>
      </aside>

      <main className="ml-64 min-h-screen">
        <header className="flex h-16 items-center justify-between border-b border-slate-800 bg-slate-950/80 px-8">
          <div>
            <h1 className="text-lg font-semibold">AI Career Agent</h1>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-cyan-500/10 text-cyan-400">
              AS
            </div>
          </div>
        </header>

        <section className="p-8">
          <Outlet />
        </section>
      </main>
    </div>
  );
}