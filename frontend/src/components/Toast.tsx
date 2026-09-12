export interface ToastMessage {
  text: string;
  tone: 'good' | 'bad';
}

export function Toast({ message }: { message: ToastMessage }) {
  return (
    <div className={message.tone === 'bad' ? 'toast toast-bad' : 'toast'} role="status">
      {message.text}
    </div>
  );
}
