import { Location } from 'react-router-dom';

export interface FromLocation {
  pathname: string;
}

export interface AuthLocationState<T = unknown> {
  from?: FromLocation;
  email?: string;
  [key: string]: any;
}

export interface LocationWithState<T = unknown> extends Location {
  state: AuthLocationState<T>;
}
