import { generateClient } from 'aws-amplify/data';
import type { Schema } from '../../amplify/data/resource';

const client = generateClient<Schema>();

export interface UserProfile {
  userId: string;
  email: string;
  fullName?: string;
  school?: string;
  gpa?: number;
  mentalHealth?: string;
  physicalHealth?: string;
  severity?: string;
  courses?: string;
}

export interface RecommendationEntry {
  userId: string;
  timestamp: string;
  recommendations: string;
  studentProfile: string;
}

// Save user profile to DynamoDB
export async function saveUserProfile(profile: UserProfile) {
  try {
    const { data, errors } = await client.models.UserProfile.create({
      userId: profile.userId,
      email: profile.email,
      fullName: profile.fullName,
      school: profile.school,
      gpa: profile.gpa,
      mentalHealth: profile.mentalHealth,
      physicalHealth: profile.physicalHealth,
      severity: profile.severity,
      courses: profile.courses,
    });
    
    if (errors) {
      console.error('Errors saving profile:', errors);
      return {
        success: false,
        error: errors[0]?.message || 'Failed to save profile',
      };
    }
    
    return {
      success: true,
      data,
    };
  } catch (error: any) {
    console.error('Error saving user profile:', error);
    return {
      success: false,
      error: error.message || 'Failed to save profile',
    };
  }
}

// Get user profile from DynamoDB
export async function getUserProfile(userId: string) {
  try {
    const { data, errors } = await client.models.UserProfile.list({
      filter: { userId: { eq: userId } },
    });
    
    if (errors) {
      return {
        success: false,
        error: errors[0]?.message || 'Failed to get profile',
      };
    }
    
    return {
      success: true,
      data: data[0] || null,
    };
  } catch (error: any) {
    console.error('Error getting user profile:', error);
    return {
      success: false,
      error: error.message || 'Failed to get profile',
    };
  }
}

// Save recommendation history
export async function saveRecommendationHistory(entry: RecommendationEntry) {
  try {
    const { data, errors } = await client.models.RecommendationHistory.create({
      userId: entry.userId,
      timestamp: entry.timestamp,
      recommendations: entry.recommendations,
      studentProfile: entry.studentProfile,
    });
    
    if (errors) {
      return {
        success: false,
        error: errors[0]?.message || 'Failed to save recommendations',
      };
    }
    
    return {
      success: true,
      data,
    };
  } catch (error: any) {
    console.error('Error saving recommendation history:', error);
    return {
      success: false,
      error: error.message || 'Failed to save recommendations',
    };
  }
}

// Get user's recommendation history
export async function getRecommendationHistory(userId: string) {
  try {
    const { data, errors } = await client.models.RecommendationHistory.list({
      filter: { userId: { eq: userId } },
    });
    
    if (errors) {
      return {
        success: false,
        error: errors[0]?.message || 'Failed to get history',
      };
    }
    
    return {
      success: true,
      data,
    };
  } catch (error: any) {
    console.error('Error getting recommendation history:', error);
    return {
      success: false,
      error: error.message || 'Failed to get history',
    };
  }
}