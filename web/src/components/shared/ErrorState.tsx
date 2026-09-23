import { Alert, AlertTitle, Button } from '@mui/material';

export function ErrorState({ error, onRetry }: { error?: Error; onRetry?: () => void }) {
  return (
    <Alert severity="error" action={onRetry ? <Button color="inherit" size="small" onClick={onRetry}>Retry</Button> : undefined}>
      <AlertTitle>Couldn’t load this view</AlertTitle>
      {error?.message ?? 'The semantic layer did not answer. Start the API on port 8080.'}
    </Alert>
  );
}
