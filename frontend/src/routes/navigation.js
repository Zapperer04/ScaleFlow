import { 
  Home, Files, GitPullRequest, Database, Search, BarChart2, Cpu, Settings
} from 'lucide-react';

export const NAVIGATION_CATEGORIES = [
  {
    id: 'experience',
    label: 'AI Document Workspace',
    items: [
      { id: 'workspace', label: 'Workspace Home', icon: Home },
      { id: 'documents', label: 'Documents Library', icon: Files }
    ]
  },
  {
    id: 'analysis',
    label: 'Deep Analysis Tools',
    items: [
      { id: 'pipelines', label: 'Pipeline DAG', icon: GitPullRequest },
      { id: 'artifacts', label: 'Artifacts Explorer', icon: Database },
      { id: 'retrieval', label: 'Retrieval Inspector', icon: Search },
      { id: 'benchmarks', label: 'System Benchmarks', icon: BarChart2 }
    ]
  },
  {
    id: 'ops',
    label: 'Platform Operations',
    items: [
      { id: 'infrastructure', label: 'System Infrastructure', icon: Cpu },
      { id: 'settings', label: 'Settings', icon: Settings }
    ]
  }
];

export const getViewDetails = (viewId) => {
  for (const cat of NAVIGATION_CATEGORIES) {
    const found = cat.items.find(item => item.id === viewId);
    if (found) return found;
  }
  return { id: viewId, label: 'Workspace View', icon: Home };
};
