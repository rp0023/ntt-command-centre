import WarningAmberRounded from '@mui/icons-material/WarningAmberRounded';
import EventBusyRounded from '@mui/icons-material/EventBusyRounded';
import FilterAltRounded from '@mui/icons-material/FilterAltRounded';
import ChecklistRounded from '@mui/icons-material/ChecklistRounded';
import ArticleRounded from '@mui/icons-material/ArticleRounded';
import AccountBalanceRounded from '@mui/icons-material/AccountBalanceRounded';
import DonutSmallRounded from '@mui/icons-material/DonutSmallRounded';
import GroupsRounded from '@mui/icons-material/GroupsRounded';
import TrendingDownRounded from '@mui/icons-material/TrendingDownRounded';
import CompareArrowsRounded from '@mui/icons-material/CompareArrowsRounded';
import SchoolRounded from '@mui/icons-material/SchoolRounded';
import type { SvgIconComponent } from '@mui/icons-material';
import type { PersonaId } from '@/types';

export interface PromptDef {
  text: string;
  icon: SvgIconComponent;
}

export const PROMPTS: Record<PersonaId, PromptDef[]> = {
  sales: [
    { text: 'Which deals are most likely to slip?', icon: WarningAmberRounded },
    { text: 'What is still open past close date?', icon: EventBusyRounded },
    { text: 'Show my funnel by stage', icon: FilterAltRounded },
    { text: 'What should I do this week?', icon: ChecklistRounded },
  ],
  executive: [
    { text: 'Give me this week’s three-line brief', icon: ArticleRounded },
    { text: 'Where is the gap to the FY26 plan?', icon: AccountBalanceRounded },
    { text: 'Which industries hold closed-won ACV?', icon: DonutSmallRounded },
    { text: 'Show the stage funnel', icon: FilterAltRounded },
  ],
  manager: [
    { text: 'Which owners concentrate stalled deals?', icon: GroupsRounded },
    { text: 'Who is walking forecast backwards?', icon: TrendingDownRounded },
    { text: 'Compare open book by owner', icon: CompareArrowsRounded },
    { text: 'Where should I coach this week?', icon: SchoolRounded },
  ],
};

export function chartPrompts(title: string): PromptDef[] {
  return [
    { text: `Main takeaway from ${title}?`, icon: ArticleRounded },
    { text: `What looks off in ${title}?`, icon: WarningAmberRounded },
    { text: `What should I do next on ${title}?`, icon: ChecklistRounded },
  ];
}
