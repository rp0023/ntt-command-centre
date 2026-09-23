import { Table, TableBody, TableCell, TableContainer, TableHead, TableRow } from '@mui/material';
import { money } from '@/utils/format';

export function DataGrid({
  rows,
  columns,
  onRow,
}: {
  rows: Record<string, unknown>[];
  columns: { key: string; label: string; money?: boolean; chip?: boolean }[];
  onRow?: (row: Record<string, unknown>) => void;
}) {
  return (
    <TableContainer sx={{ overflowX: 'auto', maxWidth: '100%' }}>
    <Table size="small">
      <TableHead>
        <TableRow>
          {columns.map((c) => (
            <TableCell key={c.key}>{c.label}</TableCell>
          ))}
        </TableRow>
      </TableHead>
      <TableBody>
        {rows.map((r, i) => (
          <TableRow key={String(r.id ?? r.opportunity_code ?? i)} hover onClick={() => onRow?.(r)} sx={{ cursor: onRow ? 'pointer' : 'default' }}>
            {columns.map((c) => {
              const v = r[c.key];
              return (
                <TableCell key={c.key}>
                  {c.money ? money(Number(v ?? 0)) : v == null ? '—' : String(v)}
                </TableCell>
              );
            })}
          </TableRow>
        ))}
      </TableBody>
    </Table>
    </TableContainer>
  );
}
