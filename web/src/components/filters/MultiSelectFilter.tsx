import { Autocomplete, Checkbox, TextField } from '@mui/material';
import CheckBoxOutlineBlankIcon from '@mui/icons-material/CheckBoxOutlineBlank';
import CheckBoxIcon from '@mui/icons-material/CheckBox';

export function MultiSelectFilter<T extends string>({
  label,
  options,
  value,
  onChange,
  width = 180,
}: {
  label: string;
  options: string[];
  value: T[];
  onChange: (next: T[]) => void;
  width?: number;
}) {
  return (
    <Autocomplete
      multiple
      disableCloseOnSelect
      size="small"
      options={options}
      value={value}
      onChange={(_, v) => onChange(v as T[])}
      limitTags={1}
      sx={{ width, minWidth: 140, flexShrink: 0 }}
      renderOption={(props, option, { selected }) => {
        const { key, ...rest } = props as { key: string } & React.HTMLAttributes<HTMLLIElement>;
        return (
          <li key={key} {...rest}>
            <Checkbox icon={<CheckBoxOutlineBlankIcon fontSize="small" />} checkedIcon={<CheckBoxIcon fontSize="small" />} checked={selected} sx={{ mr: 1 }} />
            {option}
          </li>
        );
      }}
      renderInput={(params) => <TextField {...params} label={label} placeholder={value.length ? '' : 'All'} />}
    />
  );
}
