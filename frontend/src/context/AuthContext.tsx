import React, { createContext, useContext, useEffect, useState } from 'react';
import { User, onAuthStateChanged, getIdToken } from 'firebase/auth';
import {
  auth,
  loginWithEmail,
  registerWithEmail,
  loginWithGoogle,
  logoutUser,
  resetPassword,
} from '../firebase';
import { UserProfile } from '../types';

interface AuthContextType {
  user: UserProfile | null;
  firebaseUser: User | null;
  token: string | null;
  loading: boolean;
  error: string | null;
  login: (email: string, pass: string) => Promise<void>;
  register: (email: string, pass: string, name?: string) => Promise<void>;
  loginGoogle: () => Promise<void>;
  logout: () => Promise<void>;
  clearError: () => void;
  sendResetEmail: (email: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [firebaseUser, setFirebaseUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(
      auth,
      async (currentAuthUser: User | null) => {
        setLoading(true);
        if (currentAuthUser) {
          try {
            const idToken = await getIdToken(currentAuthUser);
            setToken(idToken);
            setFirebaseUser(currentAuthUser);
            setUser({
              uid: currentAuthUser.uid,
              email: currentAuthUser.email,
              displayName:
                currentAuthUser.displayName ||
                currentAuthUser.email?.split('@')[0] ||
                'User',
              photoURL: currentAuthUser.photoURL,
            });
          } catch (err: any) {
            console.error('Failed to retrieve user token:', err);
            setToken(null);
            setUser(null);
            setFirebaseUser(null);
          }
        } else {
          setUser(null);
          setFirebaseUser(null);
          setToken(null);
        }
        setLoading(false);
      },
      (authError) => {
        console.error('Auth state listener error:', authError);
        setError(authError.message);
        setLoading(false);
      }
    );

    return () => unsubscribe();
  }, []);

  const login = async (email: string, pass: string) => {
    setError(null);
    try {
      await loginWithEmail(email, pass);
    } catch (err: any) {
      setError(formatAuthError(err));
      throw err;
    }
  };

  const register = async (email: string, pass: string, name?: string) => {
    setError(null);
    try {
      await registerWithEmail(email, pass, name);
    } catch (err: any) {
      setError(formatAuthError(err));
      throw err;
    }
  };

  const loginGoogle = async () => {
    setError(null);
    try {
      await loginWithGoogle();
    } catch (err: any) {
      setError(formatAuthError(err));
      throw err;
    }
  };

  const logout = async () => {
    setError(null);
    try {
      await logoutUser();
      setUser(null);
      setFirebaseUser(null);
      setToken(null);
    } catch (err: any) {
      setError(formatAuthError(err));
      throw err;
    }
  };

  const sendResetEmail = async (email: string) => {
    setError(null);
    try {
      await resetPassword(email);
    } catch (err: any) {
      setError(formatAuthError(err));
      throw err;
    }
  };

  const clearError = () => setError(null);

  return (
    <AuthContext.Provider
      value={{
        user,
        firebaseUser,
        token,
        loading,
        error,
        login,
        register,
        loginGoogle,
        logout,
        clearError,
        sendResetEmail,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuthContext = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuthContext must be used within an AuthProvider');
  }
  return context;
};

// Helper for human-readable Firebase Auth error messages
function formatAuthError(error: any): string {
  const code = error?.code || '';
  switch (code) {
    case 'auth/invalid-email':
      return 'Please enter a valid email address.';
    case 'auth/user-disabled':
      return 'This user account has been disabled.';
    case 'auth/user-not-found':
      return 'No account found with this email.';
    case 'auth/wrong-password':
    case 'auth/invalid-credential':
      return 'Invalid email or password.';
    case 'auth/email-already-in-use':
      return 'An account with this email already exists.';
    case 'auth/weak-password':
      return 'Password is too weak. Please use at least 6 characters.';
    case 'auth/popup-closed-by-user':
      return 'Google sign-in popup was closed before completing.';
    case 'auth/cancelled-popup-request':
      return 'Google sign-in was cancelled.';
    case 'auth/network-request-failed':
      return 'Network error. Please check your internet connection.';
    case 'auth/operation-not-allowed':
      return 'This sign-in method is not enabled in Firebase Console.';
    default:
      return error?.message || 'Authentication failed. Please try again.';
  }
}
