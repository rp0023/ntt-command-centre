import type { ReactElement } from 'react';
import SpaceDashboardRoundedIcon from '@mui/icons-material/SpaceDashboardRounded';
import PublicRoundedIcon from '@mui/icons-material/PublicRounded';
import LocalFireDepartmentRoundedIcon from '@mui/icons-material/LocalFireDepartmentRounded';
import GridViewRoundedIcon from '@mui/icons-material/GridViewRounded';
import BoltRoundedIcon from '@mui/icons-material/BoltRounded';
import FactCheckRoundedIcon from '@mui/icons-material/FactCheckRounded';
import HelpOutlineRoundedIcon from '@mui/icons-material/HelpOutlineRounded';
import type { SvgIconProps } from '@mui/material/SvgIcon';

const REGISTRY: Record<string, (p: SvgIconProps) => ReactElement> = {
  command: (p) => <SpaceDashboardRoundedIcon {...p} />,
  atlas: (p) => <PublicRoundedIcon {...p} />,
  hotspots: (p) => <LocalFireDepartmentRoundedIcon {...p} />,
  lanes: (p) => <GridViewRoundedIcon {...p} />,
  actions: (p) => <BoltRoundedIcon {...p} />,
  evidence: (p) => <FactCheckRoundedIcon {...p} />,
};

export function NavIcon({ iconKey, ...props }: { iconKey: string } & SvgIconProps): ReactElement {
  const make = REGISTRY[iconKey] ?? ((p: SvgIconProps) => <HelpOutlineRoundedIcon {...p} />);
  return make(props);
}
