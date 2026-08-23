import { doc, setDoc, getDoc, serverTimestamp } from 'firebase/firestore';
import { db } from './config';
import { UserProfile } from '../types';

export interface FirestoreUserData {
  uid: string;
  email: string | null;
  displayName: string | null;
  photoURL?: string | null;
  createdAt?: any;
  lastLoginAt?: any;
}

export const syncUserProfileToFirestore = async (
  user: UserProfile,
  isNewUser: boolean = false
): Promise<void> => {
  try {
    const userDocRef = doc(db, 'users', user.uid);
    
    if (isNewUser) {
      await setDoc(
        userDocRef,
        {
          uid: user.uid,
          email: user.email,
          displayName: user.displayName,
          photoURL: user.photoURL || null,
          createdAt: serverTimestamp(),
          lastLoginAt: serverTimestamp(),
        },
        { merge: true }
      );
    } else {
      await setDoc(
        userDocRef,
        {
          uid: user.uid,
          email: user.email,
          displayName: user.displayName,
          photoURL: user.photoURL || null,
          lastLoginAt: serverTimestamp(),
        },
        { merge: true }
      );
    }
  } catch (err) {
    console.warn('Could not sync user profile to Firestore (check Firestore permissions/rules):', err);
  }
};

export const fetchUserProfileFromFirestore = async (
  uid: string
): Promise<FirestoreUserData | null> => {
  try {
    const userDocRef = doc(db, 'users', uid);
    const snapshot = await getDoc(userDocRef);
    if (snapshot.exists()) {
      return snapshot.data() as FirestoreUserData;
    }
    return null;
  } catch (err) {
    console.warn('Could not fetch user profile from Firestore:', err);
    return null;
  }
};
