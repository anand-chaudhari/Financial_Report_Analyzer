import {
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  updateProfile,
  signOut as firebaseSignOut,
  GoogleAuthProvider,
  signInWithPopup,
  sendPasswordResetEmail,
  UserCredential,
} from 'firebase/auth';
import { auth } from './config';
import { syncUserProfileToFirestore } from './userProfile';
import { UserProfile } from '../types';

export const loginWithEmail = async (email: string, password: string): Promise<UserCredential> => {
  const credential = await signInWithEmailAndPassword(auth, email, password);
  if (credential.user) {
    const profile: UserProfile = {
      uid: credential.user.uid,
      email: credential.user.email,
      displayName: credential.user.displayName || credential.user.email?.split('@')[0] || 'User',
      photoURL: credential.user.photoURL,
    };
    await syncUserProfileToFirestore(profile, false);
  }
  return credential;
};

export const registerWithEmail = async (
  email: string,
  password: string,
  displayName?: string
): Promise<UserCredential> => {
  const credential = await createUserWithEmailAndPassword(auth, email, password);
  if (credential.user) {
    const name = displayName?.trim() || email.split('@')[0];
    try {
      await updateProfile(credential.user, { displayName: name });
    } catch (e) {
      console.warn('Could not update Auth user display name:', e);
    }

    const profile: UserProfile = {
      uid: credential.user.uid,
      email: credential.user.email,
      displayName: name,
      photoURL: credential.user.photoURL,
    };
    await syncUserProfileToFirestore(profile, true);
  }
  return credential;
};

export const loginWithGoogle = async (): Promise<UserCredential> => {
  const provider = new GoogleAuthProvider();
  provider.setCustomParameters({ prompt: 'select_account' });
  const credential = await signInWithPopup(auth, provider);
  if (credential.user) {
    const profile: UserProfile = {
      uid: credential.user.uid,
      email: credential.user.email,
      displayName: credential.user.displayName || credential.user.email?.split('@')[0] || 'User',
      photoURL: credential.user.photoURL,
    };
    await syncUserProfileToFirestore(profile, false);
  }
  return credential;
};

export const logoutUser = async (): Promise<void> => {
  await firebaseSignOut(auth);
};

export const resetPassword = async (email: string): Promise<void> => {
  await sendPasswordResetEmail(auth, email);
};

export const getCurrentUserToken = async (): Promise<string | null> => {
  const user = auth.currentUser;
  if (!user) return null;
  return await user.getIdToken();
};
