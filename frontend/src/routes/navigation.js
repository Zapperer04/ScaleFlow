import { 
  Activity, Play, Shield, Server, Film, Layers, ShieldAlert, BookOpen 
} from 'lucide-react';

export const NAVIGATION_CATEGORIES = [
  {
    id: 'main',
    label: 'Main Experience',
    items: [
      { id: 'overview', label: 'AI Document Workspace', icon: Activity }
    ]
  },
  {
    id: 'tools',
    label: 'Advanced Runtime Tools',
    items: [
      { id: 'pipelines', label: 'DAG Orchestration', icon: Play },
      { id: 'validation-lab', label: 'Validation & Chaos Lab', icon: Shield },
      { id: 'workers', label: 'Workers Registry', icon: Server },
      { id: 'replay', label: 'Replay Engine', icon: Film },
      { id: 'architecture', label: 'System Architecture', icon: Layers },
      { id: 'diagnostics', label: 'Diagnostics & DLQ', icon: ShieldAlert },
      { id: 'design-system', label: 'Design System', icon: BookOpen }
    ]
  }
];

export const getViewDetails = (viewId) => {
  for (const cat of NAVIGATION_CATEGORIES) {
    const found = cat.items.find(item => item.id === viewId);
    if (found) return found;
  }
  return { id: viewId, label: 'Workspace View', icon: Activity };
};
