jest.mock('react-router-dom', () => {
  const React = require('react');
  return {
    BrowserRouter: ({ children }) => children,
    Routes: ({ children }) => (
      <>
        {React.Children.map(children, (child) => child.props.element)}
      </>
    ),
    Route: ({ element }) => element,
    Navigate: () => null,
    Link: ({ children, to }) => <a href={to}>{children}</a>,
    useNavigate: () => jest.fn(),
  };
});

import { render, screen } from '@testing-library/react';
import App from './App';

beforeEach(() => {
  localStorage.clear();
});

test('renders login page for unauthenticated users', async () => {
  render(<App />);
  expect(await screen.findByRole('heading', { name: /login/i })).toBeInTheDocument();
});
