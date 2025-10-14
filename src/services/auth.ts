import { signIn, signOut, getCurrentUser, fetchAuthSession } from 'aws-amplify/auth';

export interface SignInParams {
  email: string;
  password: string;
}

// Sign in existing user
export async function signInUser(params: SignInParams) {
  try {
    const { email, password } = params;
    
    const { isSignedIn, nextStep } = await signIn({
      username: email,
      password,
    });
    
    return {
      success: true,
      isSignedIn,
      nextStep,
    };
  } catch (error: any) {
    console.error('Error signing in:', error);
    return {
      success: false,
      error: error.message || 'Sign in failed',
    };
  }
}

// Sign out current user
export async function signOutUser() {
  try {
    await signOut();
    return { success: true };
  } catch (error: any) {
    console.error('Error signing out:', error);
    return {
      success: false,
      error: error.message || 'Sign out failed',
    };
  }
}

// Get current authenticated user
export async function getAuthenticatedUser() {
  try {
    const user = await getCurrentUser();
    return {
      success: true,
      user,
    };
  } catch (error) {
    return {
      success: false,
      user: null,
    };
  }
}

// Get user session (for tokens)
export async function getUserSession() {
  try {
    const session = await fetchAuthSession();
    return {
      success: true,
      session,
    };
  } catch (error) {
    return {
      success: false,
      session: null,
    };
  }
}